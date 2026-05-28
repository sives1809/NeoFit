import { apiFetch } from "./client";

export type Landmark = { x: number; y: number; z: number; visibility: number };

export type FramePayload = {
  landmarks: Landmark[];
  height_cm: number;
  video_width: number;
  video_height: number;
  mode: "front" | "left_side" | "right_side";
  silhouette_chest_px?: number;
  silhouette_waist_px?: number;
  silhouette_hip_px?: number;
  silhouette_arm_left_px?: number;
  silhouette_arm_right_px?: number;
};

export type ValidationResult = {
  ok: boolean;
  reason: string;
};

export type MeasureResponse = {
  validation: ValidationResult;
  arm_left_cm?: number | null;
  arm_right_cm?: number | null;
  shoulder_cm?: number | null;
  chest_cm?: number | null;
  waist_cm?: number | null;
  hip_cm?: number | null;
  thigh_left_cm?: number | null;
  thigh_right_cm?: number | null;

  arm_side_left_cm?: number | null;
  arm_side_right_cm?: number | null;
  thigh_side_left_cm?: number | null;
  thigh_side_right_cm?: number | null;
  chest_side_cm?: number | null;
  waist_side_cm?: number | null;
  hip_side_cm?: number | null;

  confidence?: number | null;
  scale_cm_per_px?: number | null;
  stability_progress: number;
  ready_to_capture: boolean;
};

export type CapturePayload = {
  arm_left_cm?: number | null;
  arm_right_cm?: number | null;
  shoulder_cm?: number | null;
  chest_cm?: number | null;
  waist_cm?: number | null;
  hip_cm?: number | null;
  thigh_left_cm?: number | null;
  thigh_right_cm?: number | null;

  arm_side_left_cm?: number | null;
  arm_side_right_cm?: number | null;
  thigh_side_left_cm?: number | null;
  thigh_side_right_cm?: number | null;
  chest_side_cm?: number | null;
  waist_side_cm?: number | null;
  hip_side_cm?: number | null;

  confidence?: number | null;
  scale_cm_per_px?: number | null;
  frames_averaged?: number;
};

export type CombinePayload = {
  front: CapturePayload;
  left_side: CapturePayload;
  right_side: CapturePayload;
  height_cm?: number | null;
};


export const measureApi = {
  frame: (payload: FramePayload) =>
    apiFetch<MeasureResponse>("/measure/frame", { method: "POST", body: payload }),
  combine: (payload: CombinePayload) =>
    apiFetch<Record<string, any>>("/measure/combine", { method: "POST", body: payload }),
  reset: () => apiFetch<{ ok: boolean }>("/measure/reset", { method: "POST" }),
};
