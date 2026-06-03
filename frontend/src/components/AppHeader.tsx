"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { BrainCircuit, LayoutDashboard, Plus, Clock, Settings, ShieldCheck, LogOut, Activity } from "lucide-react";
import { VersionBadge } from "@/components/VersionBadge";
import { useAuth } from "@/components/providers/AuthProvider";

const baseNavItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/measurement", label: "Neue Messung", icon: Plus },
  { href: "/acousticlab", label: "AcousticLab", icon: Activity },
  { href: "/history", label: "Verlauf", icon: Clock },
  { href: "/settings", label: "Einstellungen", icon: Settings },
];

const adminNavItem = { href: "/admin", label: "Admin", icon: ShieldCheck };

export default function AppHeader() {
  const pathname = usePathname();
  const { logout, isAdmin } = useAuth();

  const navItems = isAdmin ? [...baseNavItems, adminNavItem] : baseNavItems;

  return (
    <>
      {/* Top header bar */}
      <header className="sticky top-0 z-20 bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-14">
          <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <BrainCircuit className="h-7 w-7 text-blue-600" />
            <span className="text-xl font-bold text-blue-700 tracking-tight uppercase">
              Neurolingo
            </span>
            <VersionBadge />
          </Link>

          <Button
            onClick={logout}
            variant="ghost"
            className="text-red-600 hover:text-red-700 hover:bg-red-50"
          >
            <LogOut className="h-5 w-5 mr-1.5" />
            <span className="hidden sm:inline">Abmelden</span>
          </Button>
        </div>
      </header>

      {/* Navigation bar – always visible */}
      <nav className="sticky top-14 z-10 bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2 overflow-x-auto scrollbar-hide">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-4 py-3.5 text-base font-medium whitespace-nowrap border-b-2 transition-colors ${
                    isActive
                      ? "border-blue-600 text-blue-700"
                      : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>
    </>
  );
}
