import * as React from "react";
import { Camera, CameraOff, AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLandmarkSource } from "@/lib/measure/use-landmark-source";

/**
 * WebcamStage — owns getUserMedia preview and exposes a ref + LandmarkSource
 * for the Measure page. Does NOT push frames to the backend on its own.
 */
export function useWebcamStage() {
  const videoRef = React.useRef<HTMLVideoElement | null>(null);
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null);
  const [streaming, setStreaming] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const streamRef = React.useRef<MediaStream | null>(null);
  const landmarkSource = useLandmarkSource();

  const { attach, detach } = landmarkSource;

  const start = React.useCallback(async () => {
    setError(null);
    try {
      if (typeof window === "undefined") {
        throw new Error("Cannot access camera during server rendering.");
      }
      if (!navigator?.mediaDevices?.getUserMedia) {
        throw new Error("Camera API not available. Please ensure you are on a secure connection (HTTPS) or localhost.");
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.onloadedmetadata = async () => {
          await videoRef.current?.play();
          attach(videoRef.current, canvasRef.current);
        };
        videoRef.current.srcObject = stream;
      }
      setStreaming(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Camera permission denied");
    }
  }, [attach]);

  const stop = React.useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setStreaming(false);
    detach();
  }, [detach]);

  React.useEffect(() => {
    return () => stop();
  }, [stop]);

  return { videoRef, canvasRef, streaming, error, start, stop, landmarkSource };
}

export function WebcamStage({
  videoRef,
  canvasRef,
  streaming,
  error,
  onStart,
  onStop,
  ready,
}: {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  canvasRef?: React.RefObject<HTMLCanvasElement | null>;
  streaming: boolean;
  error: string | null;
  onStart: () => void;
  onStop: () => void;
  ready: boolean;
}) {
  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-2xl border border-border/60 bg-black/60">
      {/* Video feed */}
      <video
        ref={videoRef}
        playsInline
        muted
        className="absolute inset-0 h-full w-full object-cover opacity-90"
      />
      
      {/* Skeleton Canvas Overlay */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 h-full w-full object-cover"
      />

      {/* Grid overlay */}
      <div className="pointer-events-none absolute inset-0 grid-bg opacity-60" />

      {/* Corner brackets */}
      {(["tl", "tr", "bl", "br"] as const).map((c) => (
        <span
          key={c}
          className={`pointer-events-none absolute h-6 w-6 border-primary ${
            c.includes("t") ? "top-3" : "bottom-3"
          } ${c.includes("l") ? "left-3 border-l-2 border-t-2" : "right-3 border-r-2 border-t-2"} ${
            c === "bl" ? "border-l-2 border-b-2 border-t-0" : ""
          } ${c === "br" ? "border-r-2 border-b-2 border-t-0" : ""}`}
        />
      ))}

      {/* MediaPipe pending badge */}
      {streaming && (!ready ? (
        <div className="absolute left-3 top-3 flex items-center gap-2 rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-[11px] font-medium uppercase tracking-wider text-amber-300 z-20">
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
          Initializing tracker...
        </div>
      ) : (
        <div className="absolute left-3 top-3 flex items-center gap-2 rounded-full border border-primary/40 bg-primary/10 px-3 py-1 text-[11px] font-medium uppercase tracking-wider text-primary z-20">
          <span className="h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_8px_oklch(0.88_0.24_150/0.8)]" />
          Pose tracking live
        </div>
      ))}

      {/* Idle state */}
      {!streaming ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-gradient-to-b from-black/60 via-black/40 to-black/70 text-center z-10">
          <Camera className="h-8 w-8 text-primary" />
          <p className="max-w-xs px-6 text-sm text-muted-foreground">
            Position yourself in frame. Camera runs locally — no frames leave your device.
          </p>
          <Button onClick={onStart} className="bg-primary text-primary-foreground hover:bg-primary/90">
            <Camera className="mr-2 h-4 w-4" /> Start camera
          </Button>
          {error ? <p className="mt-2 text-xs text-destructive">{error}</p> : null}
        </div>
      ) : (
        <Button
          variant="secondary"
          size="sm"
          onClick={onStop}
          className="absolute right-3 top-3 bg-background/70 backdrop-blur z-10"
        >
          <CameraOff className="mr-2 h-4 w-4" /> Stop
        </Button>
      )}
    </div>
  );
}
