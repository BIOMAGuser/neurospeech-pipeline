"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Database, Download, Loader2, Server, Check, Trash2,
  Eye, EyeOff, Users, Plus, Pencil, Shield, ShieldOff,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiFetch } from "@/lib/api";
import { useStats } from "@/hooks/queries/use-dashboard";
import { useAuth } from "@/components/providers/AuthProvider";
import { useRouter } from "next/navigation";

interface ManagedUser {
  id: number;
  username: string;
  is_active: boolean;
  is_admin: boolean;
  has_openai_key: boolean;
  created_at: string | null;
}

export default function AdminPage() {
  const { toast } = useToast();
  const { isAdmin, username } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [exporting, setExporting] = useState(false);

  // Redirect non-admins
  useEffect(() => {
    if (!isAdmin) {
      router.replace("/");
    }
  }, [isAdmin, router]);

  // React Query for stats with manual refetch
  const { data: stats, isPending: loadingStats, refetch: refetchStats } = useStats();

  // React Query for managed users list
  const { data: managedUsers, isPending: loadingUsers } = useQuery({
    queryKey: ["managed-users"],
    queryFn: async () => {
      const res = await apiFetch("/users");
      if (!res.ok) throw new Error("Fehler beim Laden der Benutzer");
      return res.json() as Promise<ManagedUser[]>;
    },
  });

  // User creation form
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newIsAdmin, setNewIsAdmin] = useState(false);

  // User edit state
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [editPassword, setEditPassword] = useState("");

  // Mutations for user management
  const createUserMutation = useMutation({
    mutationFn: async (data: { username: string; password: string; is_admin: boolean }) => {
      const res = await apiFetch("/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Fehler" }));
        throw new Error(err.detail);
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["managed-users"] });
      setShowCreateForm(false);
      setNewUsername("");
      setNewPassword("");
      setNewIsAdmin(false);
      toast({ title: "Benutzer erstellt" });
    },
    onError: (err: Error) => {
      toast({ title: "Fehler", description: err.message, variant: "destructive" });
    },
  });

  const updateUserMutation = useMutation({
    mutationFn: async ({ id, ...data }: { id: number; password?: string; is_admin?: boolean; is_active?: boolean }) => {
      const res = await apiFetch(`/users/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Fehler" }));
        throw new Error(err.detail);
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["managed-users"] });
      setEditingUserId(null);
      setEditPassword("");
      toast({ title: "Benutzer aktualisiert" });
    },
    onError: (err: Error) => {
      toast({ title: "Fehler", description: err.message, variant: "destructive" });
    },
  });

  const deleteUserMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await apiFetch(`/users/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Fehler" }));
        throw new Error(err.detail);
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["managed-users"] });
      toast({ title: "Benutzer geloescht" });
    },
    onError: (err: Error) => {
      toast({ title: "Fehler", description: err.message, variant: "destructive" });
    },
  });

  const handleExportDb = async () => {
    setExporting(true);
    try {
      const res = await apiFetch("/export");
      if (!res.ok) throw new Error("Export fehlgeschlagen");
      const data = await res.json();
      const jsonString = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonString], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `speechscribe_export_${new Date().toISOString().split("T")[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast({ title: "Export abgeschlossen", description: "Die Datenbank wurde als JSON exportiert." });
    } catch {
      toast({ title: "Export fehlgeschlagen", variant: "destructive" });
    } finally {
      setExporting(false);
    }
  };

  const handleRefreshStats = async () => {
    try {
      await refetchStats();
    } catch {
      toast({ title: "Fehler beim Laden der Statistiken", variant: "destructive" });
    }
  };

  if (!isAdmin) return null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Admin</h1>
        <p className="text-slate-600 mt-1">Benutzerverwaltung und Datenbank-Tools.</p>
      </div>

      {/* Benutzerverwaltung */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-5 w-5 text-violet-600" />
              Benutzerverwaltung
            </CardTitle>
            <Button
              size="sm"
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="bg-violet-600 hover:bg-violet-700 text-white"
            >
              <Plus className="h-4 w-4 mr-1" />
              Neuer Benutzer
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Create form */}
          {showCreateForm && (
            <div className="border border-violet-200 rounded-lg p-4 bg-violet-50 space-y-3">
              <h3 className="text-sm font-semibold text-violet-800">Neuen Benutzer anlegen</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label htmlFor="new-username" className="text-xs">Benutzername</Label>
                  <Input
                    id="new-username"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    placeholder="benutzername"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="new-password" className="text-xs">Passwort</Label>
                  <Input
                    id="new-password"
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Passwort"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="new-is-admin"
                  checked={newIsAdmin}
                  onChange={(e) => setNewIsAdmin(e.target.checked)}
                  className="rounded border-slate-300"
                />
                <Label htmlFor="new-is-admin" className="text-xs">Admin-Rechte</Label>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() =>
                    createUserMutation.mutate({
                      username: newUsername,
                      password: newPassword,
                      is_admin: newIsAdmin,
                    })
                  }
                  disabled={!newUsername.trim() || !newPassword.trim() || createUserMutation.isPending}
                  className="bg-violet-600 hover:bg-violet-700 text-white"
                >
                  {createUserMutation.isPending && <Loader2 className="h-4 w-4 mr-1 animate-spin" />}
                  Erstellen
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setShowCreateForm(false);
                    setNewUsername("");
                    setNewPassword("");
                    setNewIsAdmin(false);
                  }}
                >
                  Abbrechen
                </Button>
              </div>
            </div>
          )}

          {/* Users table */}
          {loadingUsers ? (
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" /> Lade Benutzer...
            </div>
          ) : managedUsers && managedUsers.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-slate-500">
                    <th className="pb-2 font-medium">Benutzer</th>
                    <th className="pb-2 font-medium">Rolle</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">API-Key</th>
                    <th className="pb-2 font-medium">Erstellt</th>
                    <th className="pb-2 font-medium text-right">Aktionen</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {managedUsers.map((u) => {
                    const isSelf = u.username === username;
                    return (
                    <tr key={u.id} className="hover:bg-slate-50">
                      <td className="py-2.5 font-medium text-slate-800">
                        {u.username}
                        {isSelf && <span className="ml-1.5 text-xs text-slate-400">(Sie)</span>}
                      </td>
                      <td className="py-2.5">
                        {u.is_admin ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-violet-700 bg-violet-100 px-2 py-0.5 rounded-full">
                            <Shield className="h-3 w-3" /> Admin
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full">
                            <ShieldOff className="h-3 w-3" /> Benutzer
                          </span>
                        )}
                      </td>
                      <td className="py-2.5">
                        {u.is_active ? (
                          <span className="text-emerald-600 text-xs font-medium">Aktiv</span>
                        ) : (
                          <span className="text-red-600 text-xs font-medium">Inaktiv</span>
                        )}
                      </td>
                      <td className="py-2.5">
                        {u.has_openai_key ? (
                          <Check className="h-4 w-4 text-emerald-500" />
                        ) : (
                          <span className="text-slate-400 text-xs">-</span>
                        )}
                      </td>
                      <td className="py-2.5 text-xs text-slate-500">
                        {u.created_at
                          ? new Date(u.created_at).toLocaleDateString("de-DE")
                          : "-"}
                      </td>
                      <td className="py-2.5 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {editingUserId === u.id ? (
                            <div className="flex items-center gap-1">
                              <Input
                                type="password"
                                placeholder="Neues Passwort"
                                value={editPassword}
                                onChange={(e) => setEditPassword(e.target.value)}
                                className="h-7 text-xs w-32"
                              />
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 text-xs"
                                onClick={() => {
                                  if (editPassword.trim()) {
                                    updateUserMutation.mutate({ id: u.id, password: editPassword });
                                  }
                                }}
                                disabled={!editPassword.trim() || updateUserMutation.isPending}
                              >
                                OK
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 text-xs"
                                onClick={() => {
                                  setEditingUserId(null);
                                  setEditPassword("");
                                }}
                              >
                                X
                              </Button>
                            </div>
                          ) : (
                            <>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 w-7 p-0"
                                title="Passwort aendern"
                                onClick={() => {
                                  setEditingUserId(u.id);
                                  setEditPassword("");
                                }}
                              >
                                <Pencil className="h-3.5 w-3.5" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 w-7 p-0"
                                title={isSelf ? "Eigene Rolle kann nicht geaendert werden" : u.is_admin ? "Admin-Rechte entziehen" : "Zum Admin machen"}
                                disabled={isSelf}
                                onClick={() =>
                                  updateUserMutation.mutate({ id: u.id, is_admin: !u.is_admin })
                                }
                              >
                                {u.is_admin ? (
                                  <ShieldOff className={`h-3.5 w-3.5 ${isSelf ? "text-slate-300" : "text-amber-600"}`} />
                                ) : (
                                  <Shield className={`h-3.5 w-3.5 ${isSelf ? "text-slate-300" : "text-violet-600"}`} />
                                )}
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 w-7 p-0"
                                title={isSelf ? "Eigenen Account kann man nicht deaktivieren" : u.is_active ? "Deaktivieren" : "Aktivieren"}
                                disabled={isSelf}
                                onClick={() =>
                                  updateUserMutation.mutate({ id: u.id, is_active: !u.is_active })
                                }
                              >
                                {u.is_active ? (
                                  <EyeOff className={`h-3.5 w-3.5 ${isSelf ? "text-slate-300" : "text-slate-400"}`} />
                                ) : (
                                  <Eye className={`h-3.5 w-3.5 ${isSelf ? "text-slate-300" : "text-emerald-600"}`} />
                                )}
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className={`h-7 w-7 p-0 ${isSelf ? "text-slate-300" : "text-red-500 hover:text-red-700 hover:bg-red-50"}`}
                                title={isSelf ? "Eigenen Account kann man nicht loeschen" : "Benutzer loeschen"}
                                disabled={isSelf}
                                onClick={() => {
                                  if (confirm(`Benutzer "${u.username}" wirklich loeschen?`)) {
                                    deleteUserMutation.mutate(u.id);
                                  }
                                }}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-slate-400">Keine Benutzer gefunden.</p>
          )}
        </CardContent>
      </Card>

      {/* DB Export */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Database className="h-5 w-5 text-blue-600" />
            Datenbank-Export
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-slate-600">
            Exportiert alle Patienten, Analysen und Trials als strukturierte JSON-Datei.
            Geeignet fuer Backup oder Auswertung in externen Tools.
          </p>
          <Button
            onClick={handleExportDb}
            disabled={exporting}
            className="bg-emerald-600 hover:bg-emerald-700 text-white"
          >
            {exporting ? (
              <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-1.5 h-4 w-4" />
            )}
            {exporting ? "Exportiere..." : "Gesamte Datenbank exportieren (JSON)"}
          </Button>
        </CardContent>
      </Card>

      {/* DB Stats */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Server className="h-5 w-5 text-indigo-600" />
            Datenbank-Statistiken
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {stats ? (
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <div className="text-2xl font-bold text-slate-800">{stats.patients}</div>
                <div className="text-xs text-slate-500">Patienten</div>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <div className="text-2xl font-bold text-slate-800">{stats.analyses}</div>
                <div className="text-xs text-slate-500">Analysen</div>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <div className="text-2xl font-bold text-slate-800">{stats.trials}</div>
                <div className="text-xs text-slate-500">Trials</div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              Klicken Sie auf Aktualisieren, um die aktuellen Statistiken zu laden.
            </p>
          )}
          <Button
            onClick={handleRefreshStats}
            disabled={loadingStats}
            variant="outline"
            size="sm"
          >
            {loadingStats ? (
              <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
            ) : null}
            Aktualisieren
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
