# Deep-learning visual diagnosis of TYLCV from leaf images

Transfer-learning pipeline (MobileNetV3-Small by default; ResNet-18 and EfficientNet-B0 available) that classifies a leaf photo as
`tylcv` vs `not_tylcv`, with calibrated probabilities, a validation-chosen decision threshold, duplicate-aware splits, external
(domain-shift) testing and Grad-CAM explanations.

> **Status: the pipeline is built and tested, but NO trained model with real accuracy exists yet.** The only data available in
> this project so far is 100 TYLCV-positive images and no healthy/other-disease leaves, so a diagnostic model cannot be trained
> or honestly evaluated. The unit tests use synthetic images and only prove the code runs and that splits don't leak.

## What you need to run it (on a machine with network access)

1. **A labelled dataset with negatives**, one folder per class, e.g. the tomato classes of PlantVillage
   (`Tomato___healthy`, `Tomato___Tomato_Yellow_Leaf_Curl_Virus`, and other tomato diseases as hard negatives). Check the
   dataset licence. Folders matching *yellow leaf curl / YLCV* are positives; all others are negatives.
2. **ImageNet-pretrained weights**: torchvision downloads them automatically; offline, pass `--weights path/to/state_dict.pth`.
   Without pretraining the model is trained from scratch and will be much worse (the code warns loudly).
3. **An external test set of field/phone photos** (different camera, background, lighting). The Kaggle TYLCV folder contains 9
   such images (the non-PlantVillage-named files) → use them with `--external DIR --external-label 1` for *sensitivity only*;
   add field photos of healthy and other-disease plants to measure false alarms.

```bash
pip install -r requirements-optional.txt          # torch, torchvision, scikit-learn, matplotlib, pillow
python -m dl.train --data /data/tomato --arch mobilenet_v3_small --epochs 12 --out runs/exp1 \
       --external /data/field_photos --external-label 1
python -m dl.infer --ckpt runs/exp1/model.pt --image leaf.jpg --cam cam.png
```

Outputs in `runs/exp1/`: `model.pt`, `metrics.json` (accuracy, sensitivity, specificity, F1, ROC/PR-AUC, confusion matrix on the
held-out test and external sets), `evaluation.png` (loss curves, confusion matrix, ROC, PR), `MODEL_CARD.md`.

## Design choices (and why)

- **Duplicate-aware splitting** (`data.group_split`): the Kaggle folder contains the same photo at two resolutions; random splits
  would leak such pairs across train/test and inflate accuracy.
- **Two-phase fine-tuning**: head-only for `--freeze-epochs`, then the whole network at a 10× lower learning rate.
- **Small colour jitter only**: yellowing is the diagnostic signal.
- **Temperature scaling + validation-chosen threshold** so the reported probability is calibrated and the operating point isn't
  tuned on the test set.
- **Class-weighted loss** for imbalance; **early stopping** on validation AUC.
- **Grad-CAM** to check the model looks at leaf lesions rather than background, a known failure mode for lab-background datasets.

## Known risks you must test for

- **Background/shortcut learning:** PlantVillage-style images share a uniform backdrop; a model can learn the backdrop instead of
  the disease. The external field-photo test is the guard against this.
- **Look-alikes:** other begomoviruses, nutrient deficiency and herbicide injury also curl and yellow leaves.
- **Public-dataset overlap:** other models (e.g. the Roboflow one) may have been trained on the same PlantVillage images, so
  comparing against them on those images is unfair.
- A positive result is a **screening flag; confirm by PCR/qPCR**.
