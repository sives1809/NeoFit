import * as React from "react";
import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Ruler, Salad, Sparkles, AlertCircle } from "lucide-react";
import { GlassCard, SectionHeader, StatTile, EmptyState } from "@/components/brand/GlassCard";
import { Button } from "@/components/ui/button";
import { sessionsApi } from "@/lib/api/sessions";
import { dietApi } from "@/lib/api/diet";
import { predictApi } from "@/lib/api/predict";
import { profileApi } from "@/lib/api/profile";
import { useAuth } from "@/lib/auth/store";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";


export const Route = createFileRoute("/_app/dashboard")({
  component: Dashboard,
});

function Dashboard() {
  const { user } = useAuth();
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: sessionsApi.list, retry: false });
  const diet = useQuery({ queryKey: ["diet"], queryFn: dietApi.get, retry: false });
  const prediction = useQuery({ queryKey: ["predict"], queryFn: predictApi.get, retry: false });
  const profileQuery = useQuery({ queryKey: ["profile"], queryFn: profileApi.get, retry: false });

  const latest = sessions.data?.[0];
  const measurements = latest?.measurements ?? {};

  // Compute physiological torso underestimation checks
  const heightRef = profileQuery.data?.height_cm || 171.0;
  const waistMinThresh = 70.0 * (heightRef / 171.0);
  const hipMinThresh = 80.0 * (heightRef / 171.0);
  
  const chestOk = measurements.chest_girth_cm === undefined || measurements.chest_girth_cm === null || Number(measurements.chest_girth_cm) > 80.0 * (heightRef / 171.0);
  const armOk = (measurements.arm_left_girth_cm === undefined || measurements.arm_left_girth_cm === null || Number(measurements.arm_left_girth_cm) > 22.0) &&
                (measurements.arm_right_girth_cm === undefined || measurements.arm_right_girth_cm === null || Number(measurements.arm_right_girth_cm) > 22.0);
  const thighOk = (measurements.thigh_left_girth_cm === undefined || measurements.thigh_left_girth_cm === null || Number(measurements.thigh_left_girth_cm) > 40.0) &&
                  (measurements.thigh_right_girth_cm === undefined || measurements.thigh_right_girth_cm === null || Number(measurements.thigh_right_girth_cm) > 40.0);

  const isUnderestimated = chestOk && armOk && thighOk && (
    (measurements.waist_girth_cm !== undefined && measurements.waist_girth_cm !== null && Number(measurements.waist_girth_cm) < waistMinThresh) ||
    (measurements.hip_girth_cm !== undefined && measurements.hip_girth_cm !== null && Number(measurements.hip_girth_cm) < hipMinThresh)
  );

  const underestimationReasons: string[] = [];
  if (isUnderestimated) {
    if (measurements.waist_girth_cm !== undefined && measurements.waist_girth_cm !== null && Number(measurements.waist_girth_cm) < waistMinThresh) {
      underestimationReasons.push(`Waist girth (${Number(measurements.waist_girth_cm).toFixed(1)} cm) is below physiological realism threshold (${waistMinThresh.toFixed(1)} cm)`);
    }
    if (measurements.hip_girth_cm !== undefined && measurements.hip_girth_cm !== null && Number(measurements.hip_girth_cm) < hipMinThresh) {
      underestimationReasons.push(`Hip girth (${Number(measurements.hip_girth_cm).toFixed(1)} cm) is below physiological realism threshold (${hipMinThresh.toFixed(1)} cm)`);
    }
  }

  const keyMetricsToShow = [
    { key: "chest_girth_cm", label: "Chest Girth" },
    { key: "waist_girth_cm", label: "Waist Girth" },
    { key: "hip_girth_cm", label: "Hip Girth" },
    { key: "arm_left_girth_cm", label: "L Arm Girth" },
    { key: "arm_right_girth_cm", label: "R Arm Girth" },
    { key: "thigh_left_girth_cm", label: "L Thigh Girth" },
    { key: "thigh_right_girth_cm", label: "R Thigh Girth" },
  ];

  return (
    <div>
      <SectionHeader
        title={`Welcome, ${user?.username ?? user?.email?.split("@")[0] ?? "athlete"}`}
        subtitle="Your live training overview."
        action={
          <Button asChild className="bg-primary text-primary-foreground hover:bg-primary/90">
            <Link to="/measure"><Ruler className="mr-2 h-4 w-4" /> New measurement</Link>
          </Button>
        }
      />

      {/* Latest measurements */}
      <div className="mb-8">
        {sessions.isLoading ? (
          <SkeletonRow />
        ) : latest ? (
          <div className="space-y-6">
            {/* Underestimation warning alert */}
            {isUnderestimated && (
              <div className="glass border-red-500/30 bg-red-500/5 rounded-2xl p-5 space-y-2">
                <div className="flex items-center gap-2 text-red-400 font-semibold">
                  <AlertCircle className="h-5 w-5 text-red-500 animate-pulse" />
                  <span>Calibration Warning: Torso Underestimation Suspected</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  The pseudo3D torso reconstruction returned values that are lower than expected for your height:
                </p>
                <ul className="list-disc pl-5 text-xs text-red-400/90 space-y-1">
                  {underestimationReasons.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
                <p className="text-xs text-muted-foreground mt-2">
                  Tip: Make sure to stand in A-pose with arms slightly spread away from your body for best contour width extraction.
                </p>
              </div>
            )}

            {/* Reconstructed Girths Grid */}
            <div className="glass rounded-2xl p-6">
              <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Ruler className="h-4 w-4 text-primary" /> Latest Reconstructed Girths (3D)
              </h3>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-7">
                {keyMetricsToShow.map(({ key, label }, i) => {
                  const val = measurements[key];
                  if (val === undefined || val === null) return null;
                  return (
                    <StatTile 
                      key={key} 
                      label={label} 
                      value={(val as number).toFixed(1)} 
                      unit="cm" 
                      accent={i === 0} 
                    />
                  );
                })}
              </div>
            </div>

            {/* Symmetry & Asymmetry Indicators */}
            <div className="grid gap-4 md:grid-cols-2">
              <div className="glass rounded-2xl p-5 flex flex-col justify-between">
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Arm Symmetry</h4>
                  <div className="mt-3 flex items-baseline gap-2">
                    <span className="font-mono-data text-3xl font-bold tracking-tight">
                      {measurements.arm_asymmetry_pct !== undefined && measurements.arm_asymmetry_pct !== null
                        ? `${(measurements.arm_asymmetry_pct as number).toFixed(1)}%`
                        : "—"}
                    </span>
                    <span className="text-xs text-muted-foreground">asymmetry</span>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Comparison between left arm ({measurements.arm_left_girth_cm ? `${(measurements.arm_left_girth_cm as number).toFixed(1)} cm` : "—"}) 
                    and right arm ({measurements.arm_right_girth_cm ? `${(measurements.arm_right_girth_cm as number).toFixed(1)} cm` : "—"}).
                  </p>
                </div>
                {measurements.arm_asymmetry_pct !== undefined && measurements.arm_asymmetry_pct !== null && (
                  <div className="mt-4 flex items-center">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                      Math.abs(measurements.arm_asymmetry_pct as number) <= 3.0
                        ? "bg-green-500/10 text-green-400 border border-green-500/20"
                        : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    }`}>
                      {Math.abs(measurements.arm_asymmetry_pct as number) <= 3.0 ? "Optimally Balanced" : "Minor Asymmetry Detected"}
                    </span>
                  </div>
                )}
              </div>

              <div className="glass rounded-2xl p-5 flex flex-col justify-between">
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Thigh Symmetry</h4>
                  <div className="mt-3 flex items-baseline gap-2">
                    <span className="font-mono-data text-3xl font-bold tracking-tight">
                      {measurements.thigh_asymmetry_pct !== undefined && measurements.thigh_asymmetry_pct !== null
                        ? `${(measurements.thigh_asymmetry_pct as number).toFixed(1)}%`
                        : "—"}
                    </span>
                    <span className="text-xs text-muted-foreground">asymmetry</span>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Comparison between left thigh ({measurements.thigh_left_girth_cm ? `${(measurements.thigh_left_girth_cm as number).toFixed(1)} cm` : "—"}) 
                    and right thigh ({measurements.thigh_right_girth_cm ? `${(measurements.thigh_right_girth_cm as number).toFixed(1)} cm` : "—"}).
                  </p>
                </div>
                {measurements.thigh_asymmetry_pct !== undefined && measurements.thigh_asymmetry_pct !== null && (
                  <div className="mt-4 flex items-center">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                      Math.abs(measurements.thigh_asymmetry_pct as number) <= 3.0
                        ? "bg-green-500/10 text-green-400 border border-green-500/20"
                        : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    }`}>
                      {Math.abs(measurements.thigh_asymmetry_pct as number) <= 3.0 ? "Optimally Balanced" : "Minor Asymmetry Detected"}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Width & Thickness Profiles */}
            <div className="glass rounded-2xl p-6">
              <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                Anatomical Profile (Front Width vs Side Thickness)
              </h3>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {/* Shoulder width */}
                {measurements.shoulder_cm !== undefined && measurements.shoulder_cm !== null && (
                  <div className="glass rounded-xl p-4 flex justify-between items-center">
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Shoulder Width</p>
                      <p className="mt-1 font-mono-data text-lg font-bold">{(measurements.shoulder_cm as number).toFixed(1)} cm</p>
                    </div>
                    <span className="text-xs text-muted-foreground italic">Biacromial</span>
                  </div>
                )}

                {/* Torso Profiles */}
                {[
                  { label: "Chest Torso", front: "chest_cm", side: "chest_side_left_cm" },
                  { label: "Waist Torso", front: "waist_cm", side: "waist_side_left_cm" },
                  { label: "Hip Torso", front: "hip_cm", side: "hip_side_left_cm" },
                ].map(({ label, front, side }) => {
                  const f_val = measurements[front];
                  const s_val = measurements[side];
                  if (f_val === undefined || f_val === null) return null;
                  return (
                    <div key={label} className="glass rounded-xl p-4">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
                      <div className="mt-2 flex justify-between text-sm">
                        <div>
                          <span className="text-xs text-muted-foreground mr-1">Front:</span>
                          <span className="font-mono-data font-semibold">{(f_val as number).toFixed(1)} cm</span>
                        </div>
                        {s_val !== undefined && s_val !== null && (
                          <div>
                            <span className="text-xs text-muted-foreground mr-1">Side:</span>
                            <span className="font-mono-data font-semibold">{(s_val as number).toFixed(1)} cm</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}

                {/* Limb Widths */}
                {[
                  { label: "Left Arm Profile", front: "arm_left_cm", side: "arm_side_left_cm" },
                  { label: "Right Arm Profile", front: "arm_right_cm", side: "arm_side_right_cm" },
                  { label: "Left Thigh Profile", front: "thigh_left_cm", side: "thigh_side_left_cm" },
                  { label: "Right Thigh Profile", front: "thigh_right_cm", side: "thigh_side_right_cm" },
                ].map(({ label, front, side }) => {
                  const f_val = measurements[front];
                  const s_val = measurements[side];
                  if (f_val === undefined || f_val === null) return null;
                  return (
                    <div key={label} className="glass rounded-xl p-4">
                      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
                      <div className="mt-2 flex justify-between text-sm">
                        <div>
                          <span className="text-xs text-muted-foreground mr-1">Front:</span>
                          <span className="font-mono-data font-semibold">{(f_val as number).toFixed(1)} cm</span>
                        </div>
                        {s_val !== undefined && s_val !== null && (
                          <div>
                            <span className="text-xs text-muted-foreground mr-1">Side:</span>
                            <span className="font-mono-data font-semibold">{(s_val as number).toFixed(1)} cm</span>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          <EmptyState
            title="No measurements yet"
            description="Run your first pose-based measurement to populate this dashboard."
            action={<Button asChild className="bg-primary text-primary-foreground hover:bg-primary/90"><Link to="/measure">Start measuring</Link></Button>}
          />
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-3 mb-8">
        {/* Diet card */}
        <GlassCard className="md:col-span-1 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="grid h-9 w-9 place-items-center rounded-lg border border-primary/30 bg-primary/10">
                <Salad className="h-4 w-4 text-primary" />
              </div>
              <div>
                <h3 className="font-display font-semibold text-sm">Today's Nutrition</h3>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Adaptive Macros</p>
              </div>
            </div>
            {diet.isLoading ? (
              <SkeletonRow className="mt-2" />
            ) : diet.data ? (
              <div className="grid grid-cols-2 gap-2">
                <Macro label="kcal" value={diet.data.calories} />
                <Macro label="Protein" value={diet.data.protein_g} unit="g" />
                <Macro label="Carbs" value={diet.data.carbs_g} unit="g" />
                <Macro label="Fats" value={diet.data.fats_g} unit="g" />
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No active diet plan. Set up your profile goal.</p>
            )}
          </div>
          <div className="mt-4 pt-3 border-t border-border/10 flex justify-end">
            <Button asChild variant="ghost" size="sm">
              <Link to="/diet">View Meal Details <ArrowUpRight className="ml-1 h-3.5 w-3.5" /></Link>
            </Button>
          </div>
        </GlassCard>

        {/* Symmetry overview */}
        <GlassCard className="md:col-span-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="grid h-9 w-9 place-items-center rounded-lg border border-primary/30 bg-primary/10">
                <Ruler className="h-4 w-4 text-primary" />
              </div>
              <div>
                <h3 className="font-display font-semibold text-sm">Limb Symmetry Analysis</h3>
                <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Left vs Right Balance</p>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="bg-muted/10 border border-border/20 rounded-xl p-3.5">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground">Arm Asymmetry</span>
                  <span className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                    measurements.arm_asymmetry_pct !== undefined && Math.abs(measurements.arm_asymmetry_pct as number) <= 3.0
                      ? "bg-green-500/10 text-green-400 border border-green-500/20"
                      : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                  }`}>
                    {measurements.arm_asymmetry_pct !== undefined && Math.abs(measurements.arm_asymmetry_pct as number) <= 3.0 ? "Balanced" : "Asymmetric"}
                  </span>
                </div>
                <p className="font-mono-data text-2xl font-bold mt-1 text-primary">
                  {measurements.arm_asymmetry_pct !== undefined && measurements.arm_asymmetry_pct !== null
                    ? `${(measurements.arm_asymmetry_pct as number).toFixed(1)}%`
                    : "—"}
                </p>
                <p className="text-[10px] text-muted-foreground mt-1.5">
                  L: {measurements.arm_left_girth_cm ? `${Number(measurements.arm_left_girth_cm).toFixed(1)} cm` : "—"} | R: {measurements.arm_right_girth_cm ? `${Number(measurements.arm_right_girth_cm).toFixed(1)} cm` : "—"}
                </p>
              </div>

              <div className="bg-muted/10 border border-border/20 rounded-xl p-3.5">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground">Thigh Asymmetry</span>
                  <span className={`inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium ${
                    measurements.thigh_asymmetry_pct !== undefined && Math.abs(measurements.thigh_asymmetry_pct as number) <= 3.0
                      ? "bg-green-500/10 text-green-400 border border-green-500/20"
                      : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                  }`}>
                    {measurements.thigh_asymmetry_pct !== undefined && Math.abs(measurements.thigh_asymmetry_pct as number) <= 3.0 ? "Balanced" : "Asymmetric"}
                  </span>
                </div>
                <p className="font-mono-data text-2xl font-bold mt-1 text-primary">
                  {measurements.thigh_asymmetry_pct !== undefined && measurements.thigh_asymmetry_pct !== null
                    ? `${(measurements.thigh_asymmetry_pct as number).toFixed(1)}%`
                    : "—"}
                </p>
                <p className="text-[10px] text-muted-foreground mt-1.5">
                  L: {measurements.thigh_left_girth_cm ? `${Number(measurements.thigh_left_girth_cm).toFixed(1)} cm` : "—"} | R: {measurements.thigh_right_girth_cm ? `${Number(measurements.thigh_right_girth_cm).toFixed(1)} cm` : "—"}
                </p>
              </div>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-border/10 flex justify-end">
            <Button asChild variant="ghost" size="sm">
              <Link to="/history">Full History Log <ArrowUpRight className="ml-1 h-3.5 w-3.5" /></Link>
            </Button>
          </div>
        </GlassCard>
      </div>

      {/* Advanced analytics & AI projection */}
      <div className="mb-8">
        <GlassCard className="p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <div className="flex items-center gap-2">
              <div className="grid h-9 w-9 place-items-center rounded-lg border border-primary/30 bg-primary/10">
                <Sparkles className="h-4 w-4 text-primary animate-pulse" />
              </div>
              <div>
                <h3 className="font-display font-semibold text-base">Body Analytics & AI Projections</h3>
                <p className="text-xs text-muted-foreground">Historical progression and goal-aware forecasting</p>
              </div>
            </div>

            {/* Confidence badge */}
            {prediction.data && prediction.data.status === "ok" && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground font-medium">Model Confidence:</span>
                <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
                  prediction.data.confidence === "High"
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : prediction.data.confidence === "Medium"
                    ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                    : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
                    prediction.data.confidence === "High" ? "bg-emerald-400" : prediction.data.confidence === "Medium" ? "bg-blue-400" : "bg-amber-400"
                  }`} />
                  {prediction.data.confidence}
                </span>
              </div>
            )}
          </div>

          {prediction.isLoading ? (
            <div className="h-64 animate-pulse bg-muted/10 rounded-xl flex items-center justify-center">
              <span className="text-xs text-muted-foreground">Loading prediction graphs...</span>
            </div>
          ) : prediction.data && prediction.data.status === "insufficient_data" ? (
            <div className="py-8 flex flex-col items-center justify-center text-center">
              <div className="grid h-12 w-12 place-items-center rounded-full border border-border bg-muted/10 mb-3 text-muted-foreground">
                <Sparkles className="h-6 w-6" />
              </div>
              <h4 className="font-semibold text-sm mb-1">AI Projections Locked</h4>
              <p className="text-xs text-muted-foreground max-w-sm mb-4">
                {prediction.data.message || "Need at least 5 valid sessions for progress forecasting."} 
                {" "}Keep tracking your measurements biweekly to unlock forecasting.
              </p>
              <div className="text-xs font-mono text-primary/70 bg-primary/5 border border-primary/15 rounded-md px-3 py-1.5">
                Current Valid Sessions: {sessions.data?.filter(s => {
                  const c = s.measurements?.chest_girth_cm;
                  const w = s.measurements?.waist_girth_cm;
                  const h = s.measurements?.hip_girth_cm;
                  return c !== undefined && c !== null && w !== undefined && w !== null && h !== undefined && h !== null;
                }).length ?? 0} / 5
              </div>
            </div>
          ) : prediction.data && prediction.data.status === "ok" ? (
            <DashboardAnalyticsPanel predictionData={prediction.data} />
          ) : (
            <p className="text-xs text-muted-foreground">No prediction data available.</p>
          )}
        </GlassCard>
      </div>

      {/* Recent sessions */}
      <div className="mt-8">
        <h2 className="mb-3 text-sm uppercase tracking-wider text-muted-foreground">Recent sessions</h2>
        {sessions.isLoading ? <SkeletonRow /> : (sessions.data?.length ?? 0) > 0 ? (
          <div className="grid gap-2">
            {sessions.data!.slice(0, 5).map((s) => (
              <Link key={String(s.id)} to="/history" className="glass flex items-center justify-between rounded-xl px-4 py-3 transition hover:border-primary/40">
                <div>
                  <p className="font-mono-data text-sm">Session #{String(s.id)}</p>
                  <p className="text-xs text-muted-foreground">{s.created_at ? new Date(s.created_at).toLocaleString() : "—"}</p>
                </div>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
              </Link>
            ))}
          </div>
        ) : <p className="text-sm text-muted-foreground">No sessions yet.</p>}
      </div>
    </div>
  );
}

function DashboardAnalyticsPanel({ predictionData }: { predictionData: any }) {
  const [activeTab, setActiveTab] = useState<"history" | "prediction">("history");
  const [metricGroup, setMetricGroup] = useState<"girths" | "limbs" | "bodyfat">("girths");

  const historyData = predictionData.history_chart || [];
  const predictionDataSeries = predictionData.prediction_chart || [];
  const insights = predictionData.body_comp_insights || {};

  const formatHistoryDate = (tickItem: string) => {
    try {
      const d = new Date(tickItem);
      return `${d.getMonth() + 1}/${d.getDate()}`;
    } catch {
      return tickItem;
    }
  };

  const getMetricKeys = () => {
    if (metricGroup === "girths") {
      return [
        { key: "chest", name: "Chest Girth", color: "#38bdf8" },
        { key: "waist", name: "Waist Girth", color: "#fb7185" },
        { key: "hip", name: "Hip Girth", color: "#a78bfa" },
      ];
    } else if (metricGroup === "limbs") {
      return [
        { key: "arm_left", name: "Left Arm", color: "#2dd4bf" },
        { key: "arm_right", name: "Right Arm", color: "#fbbf24" },
        { key: "thigh_left", name: "Left Thigh", color: "#f43f5e" },
        { key: "thigh_right", name: "Right Thigh", color: "#ec4899" },
      ];
    } else {
      return [
        { key: "weight", name: "Weight (kg)", color: "#10b981" },
        { key: "body_fat", name: "Body Fat (%)", color: "#8b5cf6" },
      ];
    }
  };

  const metrics = getMetricKeys();

  return (
    <div className="space-y-6">
      {/* Controls: Tab and Metric Group */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/10 pb-4">
        {/* Tab Selection */}
        <div className="flex bg-muted/20 border border-border/10 p-0.5 rounded-lg text-xs font-medium font-sans">
          <button
            onClick={() => setActiveTab("history")}
            className={`px-3 py-1.5 rounded-md transition cursor-pointer ${activeTab === "history" ? "bg-primary text-primary-foreground font-semibold shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
          >
            Historical Trends
          </button>
          <button
            onClick={() => setActiveTab("prediction")}
            className={`px-3 py-1.5 rounded-md transition cursor-pointer ${activeTab === "prediction" ? "bg-primary text-primary-foreground font-semibold shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
          >
            16-Week Projections
          </button>
        </div>

        {/* Metric Group Selector */}
        <div className="flex bg-muted/20 border border-border/10 p-0.5 rounded-lg text-xs font-medium font-sans">
          <button
            onClick={() => setMetricGroup("girths")}
            className={`px-3 py-1.5 rounded-md transition cursor-pointer ${metricGroup === "girths" ? "bg-background text-foreground border border-border/15" : "text-muted-foreground hover:text-foreground"}`}
          >
            Torso Girths
          </button>
          <button
            onClick={() => setMetricGroup("limbs")}
            className={`px-3 py-1.5 rounded-md transition cursor-pointer ${metricGroup === "limbs" ? "bg-background text-foreground border border-border/15" : "text-muted-foreground hover:text-foreground"}`}
          >
            Limbs
          </button>
          <button
            onClick={() => setMetricGroup("bodyfat")}
            className={`px-3 py-1.5 rounded-md transition cursor-pointer ${metricGroup === "bodyfat" ? "bg-background text-foreground border border-border/15" : "text-muted-foreground hover:text-foreground"}`}
          >
            Weight & Fat
          </button>
        </div>
      </div>

      {/* Chart Canvas */}
      <div className="w-full h-80 min-h-[320px] bg-muted/5 border border-border/20 rounded-xl p-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={activeTab === "history" ? historyData : predictionDataSeries}
            margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a35" opacity={0.2} />
            <XAxis
              dataKey={activeTab === "history" ? "date" : "week"}
              tickFormatter={activeTab === "history" ? formatHistoryDate : undefined}
              stroke="#888899"
              fontSize={10}
              tickLine={false}
            />
            <YAxis
              domain={["auto", "auto"]}
              stroke="#888899"
              fontSize={10}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="glass border border-border/40 p-2.5 rounded-lg text-xs shadow-lg">
                      <p className="font-semibold text-muted-foreground mb-1">
                        {activeTab === "history"
                          ? new Date(label).toLocaleDateString()
                          : `Week ${label}`}
                      </p>
                      {payload.map((p: any) => (
                        <p key={p.name} className="font-mono text-left" style={{ color: p.stroke }}>
                          {p.name}: {Number(p.value).toFixed(1)} {metricGroup === "bodyfat" && p.dataKey === "body_fat" ? "%" : (metricGroup === "bodyfat" ? "kg" : "cm")}
                        </p>
                      ))}
                    </div>
                  );
                }
                return null;
              }}
            />
            <Legend
              verticalAlign="bottom"
              height={36}
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 11, color: "#888" }}
            />
            {metrics.map((m) => (
              <Line
                key={m.key}
                type="monotone"
                dataKey={m.key}
                name={m.name}
                stroke={m.color}
                strokeWidth={2.5}
                dot={{ r: 4, strokeWidth: 1.5 }}
                activeDot={{ r: 6 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Body Composition Insights */}
      {activeTab === "prediction" && (
        <div className="bg-muted/15 border border-border/20 rounded-xl p-5">
          <h4 className="font-display font-semibold text-xs text-primary uppercase tracking-wider mb-3 flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5" /> 16-Week Body Composition Insights
          </h4>
          <div className="grid gap-3 sm:grid-cols-3 mb-4">
            <div className="bg-background/40 border border-border/10 rounded-lg p-3">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider block">Projected Muscle Change</span>
              <span className={`font-mono-data text-lg font-bold ${insights.muscle_change_kg >= 0 ? "text-emerald-400" : "text-amber-400"}`}>
                {insights.muscle_change_kg >= 0 ? `+${Number(insights.muscle_change_kg).toFixed(1)}` : Number(insights.muscle_change_kg).toFixed(1)} kg
              </span>
            </div>
            <div className="bg-background/40 border border-border/10 rounded-lg p-3">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider block">Projected Fat Change</span>
              <span className={`font-mono-data text-lg font-bold ${insights.fat_change_kg <= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                {insights.fat_change_kg > 0 ? `+${Number(insights.fat_change_kg).toFixed(1)}` : Number(insights.fat_change_kg).toFixed(1)} kg
              </span>
            </div>
            <div className="bg-background/40 border border-border/10 rounded-lg p-3">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider block">Projected Waist Change</span>
              <span className={`font-mono-data text-lg font-bold ${insights.projected_waist_change_cm <= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                {insights.projected_waist_change_cm > 0 ? `+${Number(insights.projected_waist_change_cm).toFixed(1)}` : Number(insights.projected_waist_change_cm).toFixed(1)} cm
              </span>
            </div>
          </div>
          <div className="text-xs text-muted-foreground flex gap-1.5 items-start">
            <span className="inline-block mt-0.5 text-primary">•</span>
            <span>{insights.symmetry_trend}</span>
          </div>
        </div>
      )}
    </div>
  );
}

function Macro({ label, value, unit }: { label: string; value?: number; unit?: string }) {
  return (
    <div className="glass rounded-lg p-3 text-center">
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-1 font-mono-data text-lg tabular-nums">{value ?? "—"}{unit ? <span className="ml-0.5 text-xs text-muted-foreground">{unit}</span> : null}</p>
    </div>
  );
}

function SkeletonRow({ className = "" }: { className?: string }) {
  return (
    <div className={`grid grid-cols-2 gap-3 md:grid-cols-4 ${className}`}>
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="glass h-20 animate-pulse rounded-xl" />
      ))}
    </div>
  );
}

function prettify(k: string) {
  return k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
function inferUnit(k: string) {
  if (/_cm$|height|shoulder|inseam/i.test(k)) return "cm";
  if (/_kg$|weight/i.test(k)) return "kg";
  return "";
}
