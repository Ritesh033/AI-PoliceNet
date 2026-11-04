import json, os, random, tempfile, threading, unittest, urllib.request, urllib.error

os.environ["TYLCV_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
from app import db, risk, rotation, seqtools, stacking, server  # noqa: E402


def rnd(n, seed):
    r = random.Random(seed)
    return "".join(r.choice("ACGT") for _ in range(n))


class Risk(unittest.TestCase):
    def test_temperature_shape(self):
        self.assertEqual(risk.temp_factor(5), 0)
        self.assertEqual(risk.temp_factor(25), 1)
        self.assertLess(risk.temp_factor(38), risk.temp_factor(30))

    def test_monotonic_and_modifiers(self):
        a = risk.risk_index(28, 1)["index"]
        b = risk.risk_index(28, 5)["index"]
        self.assertGreater(b, a)
        self.assertLess(risk.risk_index(28, 5, protection=0.8)["index"], b)
        self.assertLess(risk.risk_index(28, 5, exclusion=True)["index"], b)
        self.assertGreater(risk.risk_index(28, 5, "seedling")["index"], risk.risk_index(28, 5, "fruiting")["index"])

    def test_validation(self):
        with self.assertRaises(risk.ValidationError):
            risk.risk_index(28, -1)
        with self.assertRaises(risk.ValidationError):
            risk.risk_index(28, 1, stage="bogus")
        with self.assertRaises(risk.ValidationError):
            risk.risk_index(28, 1, protection=2)

    def test_season(self):
        s = risk.season_risk([{"date": "d1", "temp_c": 25, "whitefly_per_leaf": 5},
                              {"date": "d2", "temp_c": 5, "whitefly_per_leaf": 5}])
        self.assertEqual(s["summary"]["days"], 2)
        self.assertEqual(s["daily"][1]["index"], 0)


class Stacking(unittest.TestCase):
    def test_stack_increases_protection(self):
        one = stacking.plan(["Ty-1/Ty-3"])["protection"]
        two = stacking.plan(["Ty-1/Ty-3", "Ty-2"])["protection"]
        self.assertGreater(two, one)

    def test_heat_and_recombinants_penalise_ty1(self):
        base = stacking.plan(["Ty-1/Ty-3"], 25)["protection"]
        self.assertLess(stacking.plan(["Ty-1/Ty-3"], 34)["protection"], base)
        self.assertLess(stacking.plan(["Ty-1/Ty-3"], 25, True)["protection"], base)

    def test_durability_and_errors(self):
        self.assertTrue(stacking.plan(["Ty-1/Ty-3"])["durability"].startswith("Low"))
        self.assertEqual(stacking.plan(["Ty-1/Ty-3", "Ty-2", "ty-5"])["durability"], "Higher")
        with self.assertRaises(stacking.ValidationError):
            stacking.plan(["Ty-9"])

    def test_cap(self):
        self.assertLessEqual(stacking.plan(list(stacking.LOCI))["protection"], 0.95)


class Rotation(unittest.TestCase):
    def test_no_consecutive_repeats(self):
        p = [x["moa_group"] for x in rotation.plan(["4A", "28", "7C"], ["4A"], 9)["plan"]]
        self.assertNotEqual(p[0], "4A")
        self.assertTrue(all(a != b for a, b in zip(p, p[1:])))

    def test_failed_excluded_and_errors(self):
        r = rotation.plan(["4A", "28", "7C"], [], 5, failed_groups=["4A"])
        self.assertNotIn("4A", [x["moa_group"] for x in r["plan"]])
        with self.assertRaises(rotation.ValidationError):
            rotation.plan(["4A"], [], 3, failed_groups=["4A"])
        with self.assertRaises(rotation.ValidationError):
            rotation.plan(["4A"], [], 0)

    def test_single_group_warns(self):
        self.assertTrue(rotation.plan(["4A"], [], 3)["warnings"])


class Seq(unittest.TestCase):
    def setUp(self):
        self.A, self.B = rnd(2780, 1), rnd(2780, 2)

    def test_fasta_and_clean(self):
        recs = seqtools.parse_fasta(">x\nACGT\nacgu\n>y\nAAAA")
        self.assertEqual(recs[0], ("x", "ACGTACGT"))
        with self.assertRaises(seqtools.ValidationError):
            seqtools.parse_fasta("ACGT")
        with self.assertRaises(seqtools.ValidationError):
            seqtools.clean("ACGX")

    def test_classification(self):
        refs = {"A": self.A, "B": self.B}
        c = seqtools.classify(self.A[:2000] + self.A[:780], refs)
        self.assertEqual(c["best_match"], "A")
        self.assertIsNone(seqtools.classify(rnd(2780, 99), refs)["best_match"])

    def test_recombination_screen(self):
        refs = {"A": self.A, "B": self.B}
        chimera = self.A[:1400] + self.B[1400:]
        res = seqtools.recombination_screen(chimera, refs)
        self.assertTrue(res["flag"], res)
        self.assertFalse(seqtools.recombination_screen(self.A, refs)["flag"])

    def test_stats_warning(self):
        self.assertTrue(seqtools.stats("ACGT" * 10)["warnings"])


class DB(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(os.path.join(tempfile.mkdtemp(), "x.db"))

    def test_wilson(self):
        lo, hi = db.wilson(5, 10)
        self.assertLess(lo, 0.5); self.assertGreater(hi, 0.5)
        self.assertEqual(db.wilson(0, 0), (0.0, 0.0))

    def test_trials(self):
        db.add_trial(self.conn, {"site": "S1", "plants": 100, "infected": 10, "loci": "Ty-2, Ty-1/Ty-3"})
        db.add_trial(self.conn, {"site": "S2", "plants": 100, "infected": 30, "loci": "Ty-1/Ty-3,Ty-2"})
        s = db.trial_summary(self.conn)
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0]["incidence"], 0.2)
        with self.assertRaises(db.ValidationError):
            db.add_trial(self.conn, {"site": "S", "plants": 10, "infected": 11})
        self.assertIn("site", db.trials_csv(self.conn))

    def test_seedlots(self):
        db.add_seedlot(self.conn, {"lot": "L1", "tested": 0})
        db.add_seedlot(self.conn, {"lot": "L2", "tested": 1, "positive": 1})
        db.add_seedlot(self.conn, {"lot": "L3", "tested": 1, "positive": 0, "sample_size": 300})
        st = {r["lot"]: r for r in db.list_seedlots(self.conn)}
        self.assertIn("untested", st["L1"]["status"])
        self.assertIn("POSITIVE", st["L2"]["status"])
        self.assertEqual(st["L3"]["prevalence_upper95"], 0.01)
        with self.assertRaises(db.ValidationError):
            db.add_seedlot(self.conn, {"lot": "L4", "tested": 0, "positive": 2})

    def test_surveillance_flow(self):
        A, B = rnd(2780, 1), rnd(2780, 2)
        db.add_reference(self.conn, "A", "lineage-A", A)
        db.add_reference(self.conn, "B", "lineage-B", B)
        out = db.submit_sequences(self.conn, f">c1\n{A[:1400] + B[1400:]}\n>c2\n{A}", "India", "2026-01-01")
        self.assertTrue(out[0]["recombination"]["flag"])
        self.assertFalse(out[1]["recombination"]["flag"])
        s = db.surveillance_summary(self.conn)
        self.assertEqual(s["by_country"][0]["n"], 2)
        self.assertEqual(s["by_country"][0]["recombinant_flags"], 1)


class API(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = server.make_server(0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def call(self, path, body=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}",
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_pages_and_data(self):
        self.assertEqual(self.call("/")[0], 200)
        self.assertEqual(self.call("/api/health")[0], 200)
        self.assertEqual(len(json.loads(self.call("/api/evidence")[1])), 40)
        self.assertEqual(len(json.loads(self.call("/api/gaps")[1])), 7)
        self.assertEqual(self.call("/nope")[0], 404)

    def test_endpoints(self):
        s, b = self.call("/api/risk", {"temp_c": 28, "whitefly_per_leaf": 3})
        self.assertEqual(s, 200); self.assertIn("index", json.loads(b))
        s, _ = self.call("/api/risk", {"temp_c": 28, "whitefly_per_leaf": -1})
        self.assertEqual(s, 400)
        s, _ = self.call("/api/risk", {})
        self.assertEqual(s, 400)
        s, b = self.call("/api/stacking", {"selected": ["Ty-2"]})
        self.assertEqual(s, 200)
        s, b = self.call("/api/rotation", {"available_groups": ["4A", "28"], "sprays": 4})
        self.assertEqual(s, 200)
        s, _ = self.call("/api/trials", {"site": "X", "plants": 20, "infected": 5, "loci": "Ty-2"})
        self.assertEqual(s, 201)
        s, b = self.call("/api/trials/summary")
        self.assertEqual(json.loads(b)[0]["plants"], 20) if s == 200 else self.fail()
        s, _ = self.call("/api/trials", {"site": "X", "plants": 5, "infected": 9})
        self.assertEqual(s, 400)

    def test_bad_json(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/api/risk", data=b"{bad", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code, 400)


class Calibrated(unittest.TestCase):
    def synth(self, n, seed):
        import math
        r = random.Random(seed)
        rows = []
        for _ in range(n):
            T = r.uniform(18, 36); wf = r.uniform(0, 8)
            loci = [l for l in stacking.LOCI if r.random() < 0.4]
            z = -2.5 + 0.35 * wf + 0.05 * (T - 25) - 1.2 * len(loci)
            p = 1 / (1 + math.exp(-z))
            k = sum(r.random() < p for _ in range(100))
            rows.append({"temp_c": T, "whitefly_per_leaf": wf, "stage": "vegetative", "loci": loci,
                         "exclusion": False, "recombinant_pressure": False, "plants": 100, "infected": k, "p": p})
        return rows

    def test_fit_learns_direction(self):
        from app import calibrate
        m = calibrate.fit(self.synth(600, 1))
        base = {"temp_c": 28, "whitefly_per_leaf": 3, "stage": "vegetative", "exclusion": False, "recombinant_pressure": False}
        none = calibrate.predict(m, {**base, "loci": []})
        three = calibrate.predict(m, {**base, "loci": ["Ty-1/Ty-3", "Ty-2", "ty-5"]})
        self.assertLess(three, none)
        self.assertGreater(calibrate.predict(m, {**base, "loci": [], "whitefly_per_leaf": 8}), none)
        test = self.synth(300, 2)
        mae = sum(abs(calibrate.predict(m, t) - t["p"]) for t in test) / len(test)
        self.assertLess(mae, 0.08)

    def test_too_few_rows(self):
        from app import calibrate
        with self.assertRaises(ValueError):
            calibrate.fit(self.synth(10, 3))

    def test_efficacy_rotation(self):
        r = rotation.plan(["4A", "28", "7C"], ["4A"], 3, efficacy={"28": 0.3, "7C": 0.75})
        self.assertNotIn("28", [x["moa_group"] for x in r["plan"]])
        r2 = rotation.plan(["4A", "28"], [], 2, efficacy={"4A": 0.2, "28": 0.3})
        self.assertTrue(any("non-chemical" in w for w in r2["warnings"]))

    def test_v2_screen(self):
        rng = random.Random(4)
        A = "".join(rng.choice("ACGT") for _ in range(2780))
        B = list(A)
        for i in range(len(B)):
            if rng.random() < 0.04:
                B[i] = rng.choice([c for c in "ACGT" if c != B[i]])
        B = "".join(B)
        chim = A[:1200] + B[1200:1500] + A[1500:]
        self.assertTrue(seqtools.recombination_screen_v2(chim, {"A": A, "B": B})["flag"])
        self.assertFalse(seqtools.recombination_screen_v2(A, {"A": A, "B": B})["flag"])


class ModelAPI(unittest.TestCase):
    call = API.call

    @classmethod
    def setUpClass(cls):
        cls._old = db.DB_PATH
        db.DB_PATH = os.path.join(tempfile.mkdtemp(), "model.db")  # isolated database
        cls.srv = server.make_server(0)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        db.DB_PATH = cls._old

    def test_train_flow(self):
        from app import server as srv
        srv.MODEL_PATH = os.path.join(tempfile.mkdtemp(), "m.json")
        self.assertFalse(json.loads(self.call("/api/model")[1])["trained"])
        self.assertEqual(self.call("/api/model/train", {})[0], 400)  # no data yet
        r = random.Random(9)
        for _ in range(40):
            self.call("/api/trials", {"site": "s", "plants": 100, "infected": r.randint(0, 60), "mean_max_temp": r.uniform(20, 35),
                                       "whitefly_per_leaf": r.uniform(0, 6), "stage": "vegetative", "loci": "Ty-2"})
        s, b = self.call("/api/model/train", {})
        self.assertEqual(s, 200, b)
        s, b = self.call("/api/model/predict", {"temp_c": 28, "whitefly_per_leaf": 2, "loci": ["Ty-2"]})
        self.assertEqual(s, 200); self.assertIn("v2_incidence", json.loads(b))


if __name__ == "__main__":
    unittest.main()
