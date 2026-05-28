import * as React from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Trash2, Eye, Loader2, AlertCircle } from "lucide-react";
import { GlassCard, SectionHeader, EmptyState, StatTile } from "@/components/brand/GlassCard";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { sessionsApi, type Session } from "@/lib/api/sessions";
import { profileApi } from "@/lib/api/profile";


export const Route = createFileRoute("/_app/history")({
  component: HistoryPage,
});

function HistoryPage() {
  const qc = useQueryClient();
  const [active, setActive] = React.useState<Session | null>(null);
  const list = useQuery({ queryKey: ["sessions"], queryFn: sessionsApi.list, retry: false });
  const profileQuery = useQuery({ queryKey: ["profile"], queryFn: profileApi.get, retry: false });

  const del = useMutation({
    mutationFn: (id: string | number) => sessionsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["sessions"] });
      toast.success("Session deleted");
      setActive(null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // Calculate warnings for the active session
  const activeMeasurements = active?.measurements ?? {};
  const heightRef = profileQuery.data?.height_cm || 171.0;
  const waistMinThresh = 70.0 * (heightRef / 171.0);
  const hipMinThresh = 80.0 * (heightRef / 171.0);

  const chestOk = activeMeasurements.chest_girth_cm === undefined || activeMeasurements.chest_girth_cm === null || Number(activeMeasurements.chest_girth_cm) > 80.0 * (heightRef / 171.0);
  const armOk = (activeMeasurements.arm_left_girth_cm === undefined || activeMeasurements.arm_left_girth_cm === null || Number(activeMeasurements.arm_left_girth_cm) > 22.0) &&
                (activeMeasurements.arm_right_girth_cm === undefined || activeMeasurements.arm_right_girth_cm === null || Number(activeMeasurements.arm_right_girth_cm) > 22.0);
  const thighOk = (activeMeasurements.thigh_left_girth_cm === undefined || activeMeasurements.thigh_left_girth_cm === null || Number(activeMeasurements.thigh_left_girth_cm) > 40.0) &&
                  (activeMeasurements.thigh_right_girth_cm === undefined || activeMeasurements.thigh_right_girth_cm === null || Number(activeMeasurements.thigh_right_girth_cm) > 40.0);

  const isActiveUnderestimated = chestOk && armOk && thighOk && (
    (activeMeasurements.waist_girth_cm !== undefined && activeMeasurements.waist_girth_cm !== null && Number(activeMeasurements.waist_girth_cm) < waistMinThresh) ||
    (activeMeasurements.hip_girth_cm !== undefined && activeMeasurements.hip_girth_cm !== null && Number(activeMeasurements.hip_girth_cm) < hipMinThresh)
  );

  const activeUnderestimationReasons: string[] = [];
  if (isActiveUnderestimated) {
    if (activeMeasurements.waist_girth_cm !== undefined && activeMeasurements.waist_girth_cm !== null && Number(activeMeasurements.waist_girth_cm) < waistMinThresh) {
      activeUnderestimationReasons.push(`Waist girth (${Number(activeMeasurements.waist_girth_cm).toFixed(1)} cm) is below physiological realism threshold (${waistMinThresh.toFixed(1)} cm)`);
    }
    if (activeMeasurements.hip_girth_cm !== undefined && activeMeasurements.hip_girth_cm !== null && Number(activeMeasurements.hip_girth_cm) < hipMinThresh) {
      activeUnderestimationReasons.push(`Hip girth (${Number(activeMeasurements.hip_girth_cm).toFixed(1)} cm) is below physiological realism threshold (${hipMinThresh.toFixed(1)} cm)`);
    }
  }

  return (
    <div>
      <SectionHeader title="History" subtitle="Every measurement session, archived." />

      {list.isLoading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="glass h-16 animate-pulse rounded-xl" />)}</div>
      ) : (list.data?.length ?? 0) === 0 ? (
        <EmptyState title="No sessions yet" description="Your captured sessions will appear here." />
      ) : (
        <div className="grid gap-2">
          {list.data!.map((s) => (
            <div key={String(s.id)} className="glass flex items-center justify-between rounded-xl px-4 py-3">
              <div>
                <p className="font-mono-data text-sm">Session #{String(s.id)}</p>
                <p className="text-xs text-muted-foreground">{s.created_at ? new Date(s.created_at).toLocaleString() : "—"}</p>
              </div>
              <div className="flex gap-2">
                <Button size="sm" variant="ghost" onClick={() => setActive(s)}><Eye className="mr-1.5 h-4 w-4" /> View</Button>
                <Button size="sm" variant="ghost" onClick={() => del.mutate(s.id)} disabled={del.isPending} className="text-destructive hover:text-destructive">
                  {del.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Sheet open={!!active} onOpenChange={(o) => !o && setActive(null)}>
        <SheetContent className="w-full max-w-md border-l border-border/60 bg-background/95 backdrop-blur-xl overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Session Overview</SheetTitle>
          </SheetHeader>
          {active ? (
            <div className="mt-6 space-y-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Session Date & Time</p>
                <p className="text-sm text-foreground mt-1">{active.created_at ? new Date(active.created_at).toLocaleString() : "—"}</p>
              </div>

              {isActiveUnderestimated && (
                <div className="border border-red-500/20 bg-red-500/5 rounded-xl p-4 space-y-1">
                  <div className="flex items-center gap-1.5 text-red-400 text-xs font-semibold">
                    <AlertCircle className="h-4 w-4 text-red-500 animate-pulse" />
                    <span>Torso Underestimation Suspected</span>
                  </div>
                  <ul className="list-disc pl-4 text-[10px] text-red-400/80 space-y-0.5 mt-1.5">
                    {activeUnderestimationReasons.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>
              )}

              {active.measurements && Object.keys(active.measurements).length > 0 ? (
                <div className="space-y-6">
                  {/* Reconstructed Girths */}
                  {(() => {
                    const girthKeys = [
                      { key: "chest_girth_cm", label: "Chest Girth" },
                      { key: "waist_girth_cm", label: "Waist Girth" },
                      { key: "hip_girth_cm", label: "Hip Girth" },
                      { key: "arm_left_girth_cm", label: "Left Arm Girth" },
                      { key: "arm_right_girth_cm", label: "Right Arm Girth" },
                      { key: "thigh_left_girth_cm", label: "Left Thigh Girth" },
                      { key: "thigh_right_girth_cm", label: "Right Thigh Girth" },
                    ];
                    const items = girthKeys.filter(k => active.measurements![k.key] !== undefined && active.measurements![k.key] !== null);
                    if (items.length === 0) return null;
                    return (
                      <div className="space-y-2">
                        <h4 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">3D Reconstructed Girths</h4>
                        <div className="grid grid-cols-2 gap-2">
                          {items.map(({ key, label }) => (
                            <StatTile 
                              key={key} 
                              label={label} 
                              value={Number(active.measurements![key]).toFixed(1)} 
                              unit="cm"
                            />
                          ))}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Symmetry & Asymmetry */}
                  {(() => {
                    const asymKeys = [
                      { key: "arm_asymmetry_pct", label: "Arm Asymmetry" },
                      { key: "thigh_asymmetry_pct", label: "Thigh Asymmetry" },
                    ];
                    const items = asymKeys.filter(k => active.measurements![k.key] !== undefined && active.measurements![k.key] !== null);
                    if (items.length === 0) return null;
                    return (
                      <div className="space-y-2">
                        <h4 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Symmetry Metrics</h4>
                        <div className="grid grid-cols-2 gap-2">
                          {items.map(({ key, label }) => (
                            <StatTile 
                              key={key} 
                              label={label} 
                              value={Number(active.measurements![key]).toFixed(1)} 
                              unit="%"
                            />
                          ))}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Front Widths */}
                  {(() => {
                    const frontKeys = [
                      { key: "shoulder_cm", label: "Shoulder Width" },
                      { key: "chest_cm", label: "Chest Width (Front)" },
                      { key: "waist_cm", label: "Waist Width (Front)" },
                      { key: "hip_cm", label: "Hip Width (Front)" },
                      { key: "arm_left_cm", label: "L Arm Width (Front)" },
                      { key: "arm_right_cm", label: "R Arm Width (Front)" },
                      { key: "thigh_left_cm", label: "L Thigh Width (Front)" },
                      { key: "thigh_right_cm", label: "R Thigh Width (Front)" },
                    ];
                    const items = frontKeys.filter(k => active.measurements![k.key] !== undefined && active.measurements![k.key] !== null);
                    if (items.length === 0) return null;
                    return (
                      <div className="space-y-2">
                        <h4 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Front Widths</h4>
                        <div className="grid grid-cols-2 gap-2">
                          {items.map(({ key, label }) => (
                            <StatTile 
                              key={key} 
                              label={label} 
                              value={Number(active.measurements![key]).toFixed(1)} 
                              unit="cm"
                            />
                          ))}
                        </div>
                      </div>
                    );
                  })()}

                  {/* Side Thicknesses */}
                  {(() => {
                    const sideKeys = [
                      { key: "chest_side_left_cm", label: "Chest Depth (Side)" },
                      { key: "waist_side_left_cm", label: "Waist Depth (Side)" },
                      { key: "hip_side_left_cm", label: "Hip Depth (Side)" },
                      { key: "arm_side_left_cm", label: "L Arm Depth (Side)" },
                      { key: "arm_side_right_cm", label: "R Arm Depth (Side)" },
                      { key: "thigh_side_left_cm", label: "L Thigh Depth (Side)" },
                      { key: "thigh_side_right_cm", label: "R Thigh Depth (Side)" },
                    ];
                    const items = sideKeys.filter(k => active.measurements![k.key] !== undefined && active.measurements![k.key] !== null);
                    if (items.length === 0) return null;
                    return (
                      <div className="space-y-2">
                        <h4 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Side Thicknesses</h4>
                        <div className="grid grid-cols-2 gap-2">
                          {items.map(({ key, label }) => (
                            <StatTile 
                              key={key} 
                              label={label} 
                              value={Number(active.measurements![key]).toFixed(1)} 
                              unit="cm"
                            />
                          ))}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              ) : <p className="text-sm text-muted-foreground">No measurements stored.</p>}
            </div>
          ) : null}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function prettify(k: string) {
  return k.replace(/_girth_cm|_cm2|_cm|_pct|_area_cm2/g, "").replace(/_/g, " ");
}
function inferUnit(k: string) {
  if (/_cm2$|area/i.test(k)) return "cm²";
  if (/_pct$|asymmetry/i.test(k)) return "%";
  if (/_cm$|height|shoulder|arm|thigh|chest|waist|hip/i.test(k)) return "cm";
  return "";
}
