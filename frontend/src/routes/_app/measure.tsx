import * as React from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, RotateCcw, Save, AlertCircle, Crosshair } from "lucide-react";
import { GlassCard, SectionHeader, StatTile } from "@/components/brand/GlassCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useNavigate } from "@tanstack/react-router";
import { WebcamStage, useWebcamStage } from "@/components/measure/WebcamStage";
import { measureApi, type FramePayload, type MeasureResponse, type CapturePayload } from "@/lib/api/measure";
import { profileApi } from "@/lib/api/profile";
import { sessionsApi } from "@/lib/api/sessions";


export const Route = createFileRoute("/_app/measure")({
  component: MeasurePage,
});

function MeasurePage() {
  const navigate = useNavigate();
  const stage = useWebcamStage();
  const [heightCm, setHeightCm] = React.useState<number>(175);

  // Fetch profile to sync height
  const profileQuery = useQuery({
    queryKey: ["profile"],
    queryFn: profileApi.get,
    retry: false,
  });

  React.useEffect(() => {
    if (profileQuery.data?.height_cm) {
      setHeightCm(profileQuery.data.height_cm);
    }
  }, [profileQuery.data]);


  // Workflow state: front -> left_side -> right_side
  const [mode, setMode] = React.useState<"front" | "left_side" | "right_side">("front");
  const [frontPayload, setFrontPayload] = React.useState<CapturePayload | null>(null);
  const [leftSidePayload, setLeftSidePayload] = React.useState<CapturePayload | null>(null);
  const [rightSidePayload, setRightSidePayload] = React.useState<CapturePayload | null>(null);

  // Real-time backend feedback
  const [liveResponse, setLiveResponse] = React.useState<MeasureResponse | null>(null);
  const [finalResult, setFinalResult] = React.useState<Record<string, any> | null>(null);

  const frameMutation = useMutation({
    mutationFn: (payload: FramePayload) => measureApi.frame(payload),
    onSuccess: (data) => {
      console.log("[DEBUG] /measure/frame success:", data);
      setLiveResponse(data);
      if (data.ready_to_capture) {
        // Auto-capture when stable
        const payload: CapturePayload = {
          arm_left_cm: data.arm_left_cm,
          arm_right_cm: data.arm_right_cm,
          shoulder_cm: data.shoulder_cm,
          chest_cm: data.chest_cm,
          waist_cm: data.waist_cm,
          hip_cm: data.hip_cm,
          thigh_left_cm: data.thigh_left_cm,
          thigh_right_cm: data.thigh_right_cm,

          arm_side_left_cm: data.arm_side_left_cm,
          arm_side_right_cm: data.arm_side_right_cm,
          thigh_side_left_cm: data.thigh_side_left_cm,
          thigh_side_right_cm: data.thigh_side_right_cm,
          chest_side_cm: data.chest_side_cm,
          waist_side_cm: data.waist_side_cm,
          hip_side_cm: data.hip_side_cm,

          confidence: data.confidence,
          scale_cm_per_px: data.scale_cm_per_px,
        };

        if (mode === "front" && !frontPayload) {
          setFrontPayload(payload);
          toast.success("Front view captured successfully!");
          setMode("left_side");
        } else if (mode === "left_side" && !leftSidePayload) {
          setLeftSidePayload(payload);
          toast.success("Left side profile captured successfully!");
          setMode("right_side");
        } else if (mode === "right_side" && !rightSidePayload) {
          setRightSidePayload(payload);
          toast.success("Right side profile captured successfully!");
        }
      }
    },
    onError: (e: Error) => {
      console.error("[DEBUG] Frame error:", e.message, e);
    },
  });

  const combineMutation = useMutation({
    mutationFn: async () => {
      // 1. Get pseudo3d from backend
      const combined = await measureApi.combine({
        front: frontPayload!,
        left_side: leftSidePayload!,
        right_side: rightSidePayload!,
        height_cm: heightCm,
      });

      if (combined.measurement_invalid) {
        throw new Error(combined.error_message || "Measurement invalid. Torso detection failed. Please retake scan.");
      }
      // 2. Build the SessionCreate payload
      const sessionPayload = {
        // Front measurements
        arm_left_cm: frontPayload?.arm_left_cm,
        arm_right_cm: frontPayload?.arm_right_cm,
        shoulder_cm: frontPayload?.shoulder_cm,
        chest_cm: frontPayload?.chest_cm,
        waist_cm: frontPayload?.waist_cm,
        hip_cm: frontPayload?.hip_cm,
        thigh_left_cm: frontPayload?.thigh_left_cm,
        thigh_right_cm: frontPayload?.thigh_right_cm,

        // Side measurements
        arm_side_left_cm: leftSidePayload?.arm_side_left_cm || leftSidePayload?.arm_left_cm,
        arm_side_right_cm: rightSidePayload?.arm_side_right_cm || rightSidePayload?.arm_right_cm,
        thigh_side_left_cm: leftSidePayload?.thigh_side_left_cm || leftSidePayload?.thigh_left_cm,
        thigh_side_right_cm: rightSidePayload?.thigh_side_right_cm || rightSidePayload?.thigh_right_cm,

        chest_side_left_cm: leftSidePayload?.chest_side_cm,
        chest_side_right_cm: rightSidePayload?.chest_side_cm,
        waist_side_left_cm: leftSidePayload?.waist_side_cm,
        waist_side_right_cm: rightSidePayload?.waist_side_cm,
        hip_side_left_cm: leftSidePayload?.hip_side_cm,
        hip_side_right_cm: rightSidePayload?.hip_side_cm,

        // Derived pseudo-3D
        arm_left_girth_cm: combined.pseudo3d?.arm_left_girth_cm,
        arm_right_girth_cm: combined.pseudo3d?.arm_right_girth_cm,
        thigh_left_girth_cm: combined.pseudo3d?.thigh_left_girth_cm,
        thigh_right_girth_cm: combined.pseudo3d?.thigh_right_girth_cm,
        chest_girth_cm: combined.pseudo3d?.chest_girth_cm,
        waist_girth_cm: combined.pseudo3d?.waist_girth_cm,
        hip_girth_cm: combined.pseudo3d?.hip_girth_cm,

        arm_left_area_cm2: combined.pseudo3d?.arm_left_area_cm2,
        arm_right_area_cm2: combined.pseudo3d?.arm_right_area_cm2,
        thigh_left_area_cm2: combined.pseudo3d?.thigh_left_area_cm2,
        thigh_right_area_cm2: combined.pseudo3d?.thigh_right_area_cm2,
        chest_area_cm2: combined.pseudo3d?.chest_area_cm2,
        waist_area_cm2: combined.pseudo3d?.waist_area_cm2,
        hip_area_cm2: combined.pseudo3d?.hip_area_cm2,

        arm_asymmetry_pct: combined.pseudo3d?.arm_asymmetry_pct,
        thigh_asymmetry_pct: combined.pseudo3d?.thigh_asymmetry_pct,

        // Metadata
        capture_confidence: ((frontPayload?.confidence ?? 1.0) + (leftSidePayload?.confidence ?? 1.0) + (rightSidePayload?.confidence ?? 1.0)) / 3.0,
        frames_averaged: (frontPayload?.frames_averaged ?? 0) + (leftSidePayload?.frames_averaged ?? 0) + (rightSidePayload?.frames_averaged ?? 0),
      };

      // 3. Save it to the database
      await sessionsApi.create(sessionPayload);
      return combined;
    },
    onSuccess: (data) => {
      setFinalResult(data);
      toast.success("Measurements saved successfully! Redirecting...");
      setTimeout(() => navigate({ to: "/dashboard" }), 1500);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const resetMutation = useMutation({
    mutationFn: () => measureApi.reset(),
    onSuccess: () => {
      setLiveResponse(null);
      setFinalResult(null);
      setFrontPayload(null);
      setLeftSidePayload(null);
      setRightSidePayload(null);
      setMode("front");
      toast.success("Measurement state reset");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // Event-driven frame processing
  React.useEffect(() => {
    if (!stage.streaming || !stage.landmarkSource.ready || heightCm <= 0) return;
    if (stage.landmarkSource.landmarks.length !== 33) return;
    if (mode === "front" && frontPayload) return;
    if (mode === "left_side" && leftSidePayload) return;
    if (mode === "right_side" && rightSidePayload) return;
    if (frameMutation.isPending) return;

    frameMutation.mutate({
      height_cm: heightCm,
      landmarks: stage.landmarkSource.landmarks,
      video_width: stage.videoRef.current?.videoWidth || 640,
      video_height: stage.videoRef.current?.videoHeight || 480,
      mode,
      silhouette_chest_px: stage.landmarkSource.silhouetteChestPx ?? undefined,
      silhouette_waist_px: stage.landmarkSource.silhouetteWaistPx ?? undefined,
      silhouette_hip_px: stage.landmarkSource.silhouetteHipPx ?? undefined,
      silhouette_arm_left_px: stage.landmarkSource.silhouetteArmLeftPx ?? undefined,
      silhouette_arm_right_px: stage.landmarkSource.silhouetteArmRightPx ?? undefined,
    });
  }, [
    stage.streaming,
    stage.landmarkSource.ready,
    stage.landmarkSource.landmarks,
    stage.landmarkSource.silhouetteChestPx,
    stage.landmarkSource.silhouetteWaistPx,
    stage.landmarkSource.silhouetteHipPx,
    stage.landmarkSource.silhouetteArmLeftPx,
    stage.landmarkSource.silhouetteArmRightPx,
    heightCm,
    mode,
    frontPayload,
    leftSidePayload,
    rightSidePayload,
    frameMutation.isPending,
  ]);

  const canCombine = frontPayload !== null && leftSidePayload !== null && rightSidePayload !== null;

  // Render friendly state helpers for instructions
  const getWorkflowInstruction = () => {
    switch (mode) {
      case "front":
        return "Stand facing the camera squarely with your arms slightly spread out (A-pose).";
      case "left_side":
        return "Turn 90 degrees to your right (showing your LEFT side to the camera). Stand tall.";
      case "right_side":
        return "Turn 180 degrees (showing your RIGHT side to the camera). Stand tall.";
    }
  };

  return (
    <div>
      <SectionHeader
        title="Measurement Studio"
        subtitle="Pose-driven 3D body reconstruction. All processing is local and secure."
      />

      {/* Modern Premium Stepper */}
      <GlassCard className="mb-6 p-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex-1">
            <h4 className="text-xs uppercase tracking-wider font-semibold text-primary/80">Capture Status</h4>
            <p className="text-sm text-muted-foreground mt-1">{getWorkflowInstruction()}</p>
          </div>
          <div className="flex gap-2">
            <StepBadge label="1. Front" active={mode === "front"} completed={!!frontPayload} />
            <StepBadge label="2. Left Side" active={mode === "left_side"} completed={!!leftSidePayload} />
            <StepBadge label="3. Right Side" active={mode === "right_side"} completed={!!rightSidePayload} />
          </div>
        </div>
      </GlassCard>

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        {/* Stage */}
        <div className="space-y-4">
          <WebcamStage
            videoRef={stage.videoRef}
            canvasRef={stage.canvasRef}
            streaming={stage.streaming}
            error={stage.error}
            onStart={stage.start}
            onStop={stage.stop}
            ready={stage.landmarkSource.ready}
          />

          {/* HUD */}
          <GlassCard className="grid grid-cols-3 gap-3 p-4">
            <Hud label="Landmarks" value={String(stage.landmarkSource.landmarks.length)} />
            <Hud label="FPS" value={stage.landmarkSource.fps.toFixed(0)} />
            <Hud label="State" value={stage.streaming ? (stage.landmarkSource.ready ? `Tracking ${mode.replace("_", " ")}` : "Initializing...") : "Idle"} />
          </GlassCard>
        </div>

        {/* Controls */}
        <div className="space-y-4">
          <GlassCard>
            <h3 className="font-display text-lg font-semibold">Subject Height</h3>
            <p className="text-xs text-muted-foreground">Required for scale factor calibration.</p>
            <div className="mt-4 space-y-1.5">
              <Label htmlFor="height">Height (cm)</Label>
              <Input
                id="height"
                type="number"
                min={80}
                max={250}
                value={heightCm}
                onChange={(e) => setHeightCm(Number(e.target.value))}
              />
            </div>
          </GlassCard>

          <GlassCard>
            <h3 className="font-display text-lg font-semibold">Stability Calibration</h3>
            <p className="text-xs text-muted-foreground">Hold pose steady once validation indicator turns green.</p>

            {/* Live Feedback */}
            {liveResponse && !canCombine && stage.streaming && (
              <div className="mt-3 rounded-md border border-border/40 bg-background/50 p-3">
                <div className="flex items-center justify-between text-xs">
                  <span className={`font-semibold flex items-center gap-1.5 ${liveResponse.validation.ok ? "text-emerald-400" : "text-amber-400"}`}>
                    <span className={`w-2 h-2 rounded-full ${liveResponse.validation.ok ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
                    {liveResponse.validation.ok ? "Pose Calibrated — Hold Still" : "Adjusting Alignment..."}
                  </span>
                  <span className="text-muted-foreground font-mono">{(liveResponse.stability_progress * 100).toFixed(0)}%</span>
                </div>
                {!liveResponse.validation.ok && liveResponse.validation.reason && (
                  <p className="mt-1.5 text-xs text-amber-400/90">{liveResponse.validation.reason}</p>
                )}
                <div className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-secondary">
                  <div 
                    className="h-full bg-gradient-to-r from-cyan-500 to-indigo-500 transition-all duration-300"
                    style={{ width: `${liveResponse.stability_progress * 100}%` }}
                  />
                </div>
              </div>
            )}

            <div className="mt-4 space-y-2">
              <Button
                onClick={() => combineMutation.mutate()}
                disabled={!canCombine || combineMutation.isPending}
                className="w-full bg-gradient-to-r from-emerald-500 to-teal-500 text-white font-semibold shadow-lg hover:brightness-110 disabled:opacity-40"
              >
                {combineMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                Combine & Save Session
              </Button>
              <Button
                onClick={() => resetMutation.mutate()}
                disabled={resetMutation.isPending}
                variant="ghost"
                className="w-full border border-border/60 hover:bg-background/20"
              >
                {resetMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RotateCcw className="mr-2 h-4 w-4" />}
                Reset All Steps
              </Button>
            </div>
          </GlassCard>

          <GlassCard>
            <h3 className="font-display text-lg font-semibold">Reconstructed Metrics</h3>
            {finalResult && finalResult.pseudo3d && finalResult.pseudo3d.underestimation_detected && (
              <div className="mt-3 p-3 rounded-md bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs flex gap-2 items-start">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold block mb-0.5">Torso Underestimation Suspected</span>
                  {finalResult.pseudo3d.underestimation_warning}
                </div>
              </div>
            )}
            {finalResult && finalResult.pseudo3d ? (

              <div className="mt-4 grid grid-cols-2 gap-2 max-h-64 overflow-y-auto pr-1">
                {Object.entries(finalResult.pseudo3d).map(([k, v]) => {
                  if (v === null || typeof v !== "number") return null;
                  return (
                    <StatTile
                      key={k}
                      label={k.replace(/_girth_cm|_cm2|_cm|_pct|_area_cm2/g, "").replace(/_/g, " ")}
                      value={v.toFixed(1)}
                      unit={/girth|shoulder|arm|thigh|chest|waist|hip/i.test(k) ? (/area|cm2/i.test(k) ? "cm²" : "cm") : "%"}
                    />
                  );
                })}
              </div>
            ) : liveResponse ? (
              <div className="mt-4 grid grid-cols-2 gap-2 opacity-80">
                <StatTile label="L Arm Width" value={liveResponse.arm_left_cm?.toFixed(1) ?? "—"} unit="cm" />
                <StatTile label="R Arm Width" value={liveResponse.arm_right_cm?.toFixed(1) ?? "—"} unit="cm" />
                <StatTile label="L Thigh Width" value={liveResponse.thigh_left_cm?.toFixed(1) ?? "—"} unit="cm" />
                <StatTile label="R Thigh Width" value={liveResponse.thigh_right_cm?.toFixed(1) ?? "—"} unit="cm" />
                <StatTile label="Shoulder Width" value={liveResponse.shoulder_cm?.toFixed(1) ?? "—"} unit="cm" />
                <StatTile label="Quality Score" value={liveResponse.confidence?.toFixed(2) ?? "—"} />
              </div>
            ) : (
              <p className="mt-3 text-sm text-muted-foreground">Start the camera stream to initialize live feedback.</p>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
}

function StepBadge({ label, active, completed }: { label: string; active: boolean; completed: boolean }) {
  let bg = "bg-background/40 text-muted-foreground border border-border/30";
  if (completed) {
    bg = "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40";
  } else if (active) {
    bg = "bg-primary/20 text-primary border border-primary/50 shadow-[0_0_8px_rgba(59,130,246,0.3)]";
  }

  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold uppercase transition-all duration-300 ${bg}`}>
      {label}
    </span>
  );
}

function Hud({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">{label}</p>
      <p className="mt-0.5 font-mono text-base font-bold text-foreground/90">{value}</p>
    </div>
  );
}
