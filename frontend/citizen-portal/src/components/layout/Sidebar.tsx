"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: "D" },
  { href: "/complaints", label: "My Complaints", icon: "C" },
  { href: "/complaints/new", label: "File Complaint", icon: "+" },
  { href: "/evidence", label: "Evidence", icon: "E" },
  { href: "/profile", label: "Profile", icon: "P" },
  { href: "/emergency", label: "Emergency", icon: "!" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen">
      <div className="p-6">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-primary-500 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold">AP</span>
          </div>
          <div>
            <h2 className="font-bold text-gray-900">AI PoliceNet</h2>
            <p className="text-xs text-gray-500">Citizen Portal</p>
          </div>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary-50 text-primary-600"
                    : "text-gray-600 hover:bg-gray-50"
                }`}
              >
                <span className={`w-8 h-8 rounded-md flex items-center justify-center text-xs font-bold ${
                  isActive ? "bg-primary-500 text-white" : "bg-gray-100 text-gray-500"
                }`}>
                  {item.icon}
                </span>
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="absolute bottom-0 w-64 p-6 border-t border-gray-200">
        <button
          onClick={() => {
            localStorage.clear();
            window.location.href = "/";
          }}
          className="text-sm text-gray-500 hover:text-danger-500 transition-colors"
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
