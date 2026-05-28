import * as React from "react";
import type { Landmark } from "@/lib/api/measure";
import { Pose, POSE_CONNECTIONS } from "@mediapipe/pose";
import { drawConnectors, drawLandmarks } from "@mediapipe/drawing_utils";

export type LandmarkSource = {
  ready: boolean;
  landmarks: Landmark[];
  fps: number;
  silhouetteChestPx: number | null;
  silhouetteWaistPx: number | null;
  silhouetteHipPx: number | null;
  silhouetteArmLeftPx: number | null;
  silhouetteArmRightPx: number | null;
  /** Attach to a <video> element once camera stream is live. */
  attach: (video: HTMLVideoElement | null, canvas: HTMLCanvasElement | null) => void;
  detach: () => void;
};

export function useLandmarkSource(): LandmarkSource {
  const [landmarks, setLandmarks] = React.useState<Landmark[]>([]);
  const [fps, setFps] = React.useState(0);
  const [ready, setReady] = React.useState(false);
  const [silhouetteChestPx, setSilhouetteChestPx] = React.useState<number | null>(null);
  const [silhouetteWaistPx, setSilhouetteWaistPx] = React.useState<number | null>(null);
  const [silhouetteHipPx, setSilhouetteHipPx] = React.useState<number | null>(null);
  const [silhouetteArmLeftPx, setSilhouetteArmLeftPx] = React.useState<number | null>(null);
  const [silhouetteArmRightPx, setSilhouetteArmRightPx] = React.useState<number | null>(null);

  const poseRef = React.useRef<Pose | null>(null);
  const reqRef = React.useRef<number>(0);
  const videoRef = React.useRef<HTMLVideoElement | null>(null);
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null);
  const offscreenCanvasRef = React.useRef<HTMLCanvasElement | null>(null);

  const getSilhouetteWidthAtY = React.useCallback((
    segmentationMask: any,
    yRatio: number,
    w: number,
    h: number,
    xMinLimit?: number,
    xMaxLimit?: number,
    torsoLms?: {
      left_shoulder: { x: number; y: number };
      right_shoulder: { x: number; y: number };
      left_hip: { x: number; y: number };
      right_hip: { x: number; y: number };
    },
    isSideView?: boolean
  ): number | null => {
    if (!segmentationMask) return null;
    if (!offscreenCanvasRef.current) {
      offscreenCanvasRef.current = document.createElement("canvas");
    }
    const offscreen = offscreenCanvasRef.current;
    if (offscreen.width !== w || offscreen.height !== h) {
      offscreen.width = w;
      offscreen.height = h;
    }
    const ctx = offscreen.getContext("2d");
    if (!ctx) return null;
    
    // Clear context to prevent drawing over old frames
    ctx.clearRect(0, 0, w, h);
    
    if (torsoLms) {
      if (isSideView) {
        // Construct side view torso polygon centered on shoulder-hip center line
        const x_sh_avg = (torsoLms.left_shoulder.x + torsoLms.right_shoulder.x) / 2;
        const x_hip_avg = (torsoLms.left_hip.x + torsoLms.right_hip.x) / 2;
        
        const dy_torso = ((torsoLms.left_hip.y + torsoLms.right_hip.y) - 
                          (torsoLms.left_shoulder.y + torsoLms.right_shoulder.y)) / 2;
                          
        const side_pad_top = 0.15; // top horizontal padding in terms of dy_torso
        const side_pad_bottom = 0.15; // bottom horizontal padding in terms of dy_torso
        const vertical_pad_ratio = 0.02; // vertical padding
        
        const y_top = (torsoLms.left_shoulder.y + torsoLms.right_shoulder.y) / 2 - dy_torso * vertical_pad_ratio;
        const y_bottom = (torsoLms.left_hip.y + torsoLms.right_hip.y) / 2 + dy_torso * vertical_pad_ratio;
        
        const ls_padded = {
          x: (x_sh_avg - dy_torso * side_pad_top) * w,
          y: y_top * h
        };
        const rs_padded = {
          x: (x_sh_avg + dy_torso * side_pad_top) * w,
          y: y_top * h
        };
        const lh_padded = {
          x: (x_hip_avg - dy_torso * side_pad_bottom) * w,
          y: y_bottom * h
        };
        const rh_padded = {
          x: (x_hip_avg + dy_torso * side_pad_bottom) * w,
          y: y_bottom * h
        };
        
        ctx.beginPath();
        ctx.moveTo(ls_padded.x, ls_padded.y);
        ctx.lineTo(rs_padded.x, rs_padded.y);
        ctx.lineTo(rh_padded.x, rh_padded.y);
        ctx.lineTo(lh_padded.x, lh_padded.y);
        ctx.closePath();
        ctx.fillStyle = "white";
        ctx.fill();
      } else {
        // Construct front view torso polygon
        const dx_sh = torsoLms.right_shoulder.x - torsoLms.left_shoulder.x;
        const dy_sh = torsoLms.right_shoulder.y - torsoLms.left_shoulder.y;
        const dx_hip = torsoLms.left_hip.x - torsoLms.right_hip.x;
        const dy_hip = torsoLms.left_hip.y - torsoLms.right_hip.y;

        const pad_ratio = 0.22;
        const vertical_pad_ratio = 0.15;

        const dy_torso = ((torsoLms.left_hip.y + torsoLms.right_hip.y) - 
                          (torsoLms.left_shoulder.y + torsoLms.right_shoulder.y)) / 2;

        const ls_padded = {
          x: (torsoLms.left_shoulder.x - dx_sh * pad_ratio) * w,
          y: (torsoLms.left_shoulder.y - dy_torso * vertical_pad_ratio) * h
        };
        const rs_padded = {
          x: (torsoLms.right_shoulder.x + dx_sh * pad_ratio) * w,
          y: (torsoLms.right_shoulder.y - dy_torso * vertical_pad_ratio) * h
        };
        const lh_padded = {
          x: (torsoLms.left_hip.x - dx_hip * pad_ratio) * w,
          y: (torsoLms.left_hip.y + dy_torso * vertical_pad_ratio) * h
        };
        const rh_padded = {
          x: (torsoLms.right_hip.x + dx_hip * pad_ratio) * w,
          y: (torsoLms.right_hip.y + dy_torso * vertical_pad_ratio) * h
        };

        ctx.beginPath();
        ctx.moveTo(ls_padded.x, ls_padded.y);
        ctx.lineTo(rs_padded.x, rs_padded.y);
        ctx.lineTo(rh_padded.x, rh_padded.y);
        ctx.lineTo(lh_padded.x, lh_padded.y);
        ctx.closePath();
        ctx.fillStyle = "white";
        ctx.fill();
      }

      ctx.globalCompositeOperation = "source-in";
      ctx.drawImage(segmentationMask, 0, 0, w, h);
      ctx.globalCompositeOperation = "source-over";
    } else {
      ctx.drawImage(segmentationMask, 0, 0, w, h);
    }
    
    const yPixelCenter = Math.floor(yRatio * h);
    // 7-row median row-sampling (target row ± 3 pixels)
    const startY = Math.max(0, yPixelCenter - 3);
    const endY = Math.min(h - 1, yPixelCenter + 3);
    const rowCount = endY - startY + 1;
    
    if (rowCount <= 0) return null;
    
    try {
      const imgData = ctx.getImageData(0, startY, w, rowCount);
      const data = imgData.data; // w * rowCount * 4 bytes
      
      const widths: number[] = [];
      const startX = xMinLimit !== undefined ? Math.max(0, Math.floor(xMinLimit)) : 0;
      const endX = xMaxLimit !== undefined ? Math.min(w - 1, Math.floor(xMaxLimit)) : w - 1;
      
      for (let row = 0; row < rowCount; row++) {
        const rowOffset = row * w * 4;
        let longestLength = 0;
        let currentStart = -1;
        
        for (let x = startX; x <= endX; x++) {
          const val = data[rowOffset + x * 4]; // Red channel
          if (val > 100) {
            if (currentStart === -1) {
              currentStart = x;
            }
          } else {
            if (currentStart !== -1) {
              const len = x - currentStart;
              if (len > longestLength) {
                longestLength = len;
              }
              currentStart = -1;
            }
          }
        }
        if (currentStart !== -1) {
          const len = (endX + 1) - currentStart;
          if (len > longestLength) {
            longestLength = len;
          }
        }
        
        if (longestLength > 0) {
          widths.push(longestLength);
        }
      }
      
      if (widths.length > 0) {
        widths.sort((a, b) => a - b);
        const mid = Math.floor(widths.length / 2);
        if (widths.length % 2 !== 0) {
          return widths[mid];
        } else {
          return (widths[mid - 1] + widths[mid]) / 2;
        }
      }
    } catch (e) {
      console.error("Failed to read segmentation mask pixel data", e);
    }
    return null;
  }, []);

  const getArmSilhouetteWidthAtY = React.useCallback((
    segmentationMask: any,
    shoulder: { x: number; y: number },
    elbow: { x: number; y: number },
    w: number,
    h: number,
    xMinLimit?: number,
    xMaxLimit?: number
  ): number | null => {
    if (!segmentationMask) return null;
    if (!offscreenCanvasRef.current) {
      offscreenCanvasRef.current = document.createElement("canvas");
    }
    const offscreen = offscreenCanvasRef.current;
    if (offscreen.width !== w || offscreen.height !== h) {
      offscreen.width = w;
      offscreen.height = h;
    }
    const ctx = offscreen.getContext("2d");
    if (!ctx) return null;
    
    ctx.clearRect(0, 0, w, h);
    
    const dx = elbow.x - shoulder.x;
    const dy = elbow.y - shoulder.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (len === 0) return null;
    
    const dirX = dx / len;
    const dirY = dy / len;
    const perpX = -dirY;
    const perpY = dirX;
    
    const lenPad = len * 0.1;
    const perpPad = len * 0.25;
    
    const s1 = {
      x: (shoulder.x - lenPad * dirX + perpPad * perpX) * w,
      y: (shoulder.y - lenPad * dirY + perpPad * perpY) * h
    };
    const s2 = {
      x: (shoulder.x - lenPad * dirX - perpPad * perpX) * w,
      y: (shoulder.y - lenPad * dirY - perpPad * perpY) * h
    };
    const e1 = {
      x: (elbow.x + lenPad * dirX + perpPad * perpX) * w,
      y: (elbow.y + lenPad * dirY + perpPad * perpY) * h
    };
    const e2 = {
      x: (elbow.x + lenPad * dirX - perpPad * perpX) * w,
      y: (elbow.y + lenPad * dirY - perpPad * perpY) * h
    };
    
    ctx.beginPath();
    ctx.moveTo(s1.x, s1.y);
    ctx.lineTo(s2.x, s2.y);
    ctx.lineTo(e2.x, e2.y);
    ctx.lineTo(e1.x, e1.y);
    ctx.closePath();
    ctx.fillStyle = "white";
    ctx.fill();
    
    ctx.globalCompositeOperation = "source-in";
    ctx.drawImage(segmentationMask, 0, 0, w, h);
    ctx.globalCompositeOperation = "source-over";
    
    const yRatio = (shoulder.y + elbow.y) / 2;
    const yPixelCenter = Math.floor(yRatio * h);
    
    const startY = Math.max(0, yPixelCenter - 3);
    const endY = Math.min(h - 1, yPixelCenter + 3);
    const rowCount = endY - startY + 1;
    
    if (rowCount <= 0) return null;
    
    try {
      const imgData = ctx.getImageData(0, startY, w, rowCount);
      const data = imgData.data;
      
      const widths: number[] = [];
      const startX = xMinLimit !== undefined ? Math.max(0, Math.floor(xMinLimit)) : 0;
      const endX = xMaxLimit !== undefined ? Math.min(w - 1, Math.floor(xMaxLimit)) : w - 1;
      
      for (let row = 0; row < rowCount; row++) {
        const rowOffset = row * w * 4;
        let longestLength = 0;
        let currentStart = -1;
        
        for (let x = startX; x <= endX; x++) {
          const val = data[rowOffset + x * 4];
          if (val > 100) {
            if (currentStart === -1) {
              currentStart = x;
            }
          } else {
            if (currentStart !== -1) {
              const lenVal = x - currentStart;
              if (lenVal > longestLength) {
                longestLength = lenVal;
              }
              currentStart = -1;
            }
          }
        }
        if (currentStart !== -1) {
          const lenVal = (endX + 1) - currentStart;
          if (lenVal > longestLength) {
            longestLength = lenVal;
          }
        }
        
        if (longestLength > 0) {
          widths.push(longestLength);
        }
      }
      
      if (widths.length > 0) {
        widths.sort((a, b) => a - b);
        const mid = Math.floor(widths.length / 2);
        if (widths.length % 2 !== 0) {
          return widths[mid];
        } else {
          return (widths[mid - 1] + widths[mid]) / 2;
        }
      }
    } catch (e) {
      console.error("Failed to read segmentation mask pixel data for arm", e);
    }
    return null;
  }, []);


  const frameTimeRef = React.useRef<number>(typeof performance !== "undefined" ? performance.now() : 0);
  const framesRef = React.useRef<number>(0);

  const processFrame = React.useCallback(async () => {
    if (videoRef.current && poseRef.current && videoRef.current.readyState >= 2) {
      await poseRef.current.send({ image: videoRef.current });
    }
    reqRef.current = requestAnimationFrame(processFrame);
  }, []);

  const attach = React.useCallback((video: HTMLVideoElement | null, canvas: HTMLCanvasElement | null) => {
    videoRef.current = video;
    canvasRef.current = canvas;

    if (!video || !canvas) return;

    if (!poseRef.current) {
      const pose = new Pose({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`,
      });

      pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: true,
        smoothSegmentation: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5,
      });

      pose.onResults((results) => {
        // Calculate FPS
        framesRef.current++;
        const now = performance.now();
        if (now - frameTimeRef.current >= 1000) {
          setFps(Math.round((framesRef.current * 1000) / (now - frameTimeRef.current)));
          framesRef.current = 0;
          frameTimeRef.current = now;
        }

        if (!ready) setReady(true);

        const canvasCtx = canvasRef.current?.getContext("2d");
        if (canvasCtx && canvasRef.current && videoRef.current) {
          canvasRef.current.width = videoRef.current.videoWidth;
          canvasRef.current.height = videoRef.current.videoHeight;
          canvasCtx.save();
          canvasCtx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
          
          if (results.poseLandmarks) {
            drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS, { color: "#00FF00", lineWidth: 2 });
            drawLandmarks(canvasCtx, results.poseLandmarks, { color: "#FF0000", lineWidth: 1, radius: 2 });
            
            // Map to our Landmark type, clamping to [0, 1] for strict backend validation
            setLandmarks(results.poseLandmarks.map(lm => ({
              x: Math.max(0, Math.min(1, lm.x)),
              y: Math.max(0, Math.min(1, lm.y)),
              z: lm.z,
              visibility: Math.max(0, Math.min(1, lm.visibility ?? 1.0))
            })));

            // Compute silhouette widths from segmentation mask
            if (results.segmentationMask && results.poseLandmarks.length >= 33) {
              const lms = results.poseLandmarks;
              const y_shoulder = (lms[11].y + lms[12].y) / 2;
              const y_hip = (lms[23].y + lms[24].y) / 2;
              const torso_y_span = y_hip - y_shoulder;

              if (torso_y_span > 0) {
                const y_chest = y_shoulder + 0.25 * torso_y_span;
                const y_waist = y_shoulder + 0.65 * torso_y_span;
                const y_hip_anatomical = y_hip;

                const w_val = videoRef.current.videoWidth;
                const h_val = videoRef.current.videoHeight;

                // Determine if front view or side view based on shoulder width on X axis
                const sh_w_norm = Math.abs(lms[11].x - lms[12].x);
                const isSideView = sh_w_norm < 0.15;

                let chestMin: number | undefined;
                let chestMax: number | undefined;
                let waistMin: number | undefined;
                let waistMax: number | undefined;
                let hipMin: number | undefined;
                let hipMax: number | undefined;

                if (isSideView) {
                  // Side view: scan 25% of width to left/right of center
                  const x_center = (lms[11].x + lms[12].x + lms[23].x + lms[24].x) / 4.0;
                  chestMin = (x_center - 0.25) * w_val;
                  chestMax = (x_center + 0.25) * w_val;
                  waistMin = (x_center - 0.25) * w_val;
                  waistMax = (x_center + 0.25) * w_val;
                  hipMin = (x_center - 0.25) * w_val;
                  hipMax = (x_center + 0.25) * w_val;
                } else {
                  // Front view: limit search window to ignore arms
                  const x_left_chest = Math.min(lms[11].x, lms[12].x);
                  const x_right_chest = Math.max(lms[11].x, lms[12].x);
                  const chest_span = x_right_chest - x_left_chest;
                  chestMin = (x_left_chest - chest_span * 0.2) * w_val;
                  chestMax = (x_right_chest + chest_span * 0.2) * w_val;

                  const x_left_waist = Math.min(lms[11].x, lms[12].x, lms[23].x, lms[24].x);
                  const x_right_waist = Math.max(lms[11].x, lms[12].x, lms[23].x, lms[24].x);
                  const waist_span = x_right_waist - x_left_waist;
                  waistMin = (x_left_waist - waist_span * 0.2) * w_val;
                  waistMax = (x_right_waist + waist_span * 0.2) * w_val;

                  const x_left_hip = Math.min(lms[23].x, lms[24].x);
                  const x_right_hip = Math.max(lms[23].x, lms[24].x);
                  const hip_span = x_right_hip - x_left_hip;
                  hipMin = (x_left_hip - hip_span * 0.25) * w_val;
                  hipMax = (x_right_hip + hip_span * 0.25) * w_val;
                }

                const torsoLms = {
                  left_shoulder: { x: lms[11].x, y: lms[11].y },
                  right_shoulder: { x: lms[12].x, y: lms[12].y },
                  left_hip: { x: lms[23].x, y: lms[23].y },
                  right_hip: { x: lms[24].x, y: lms[24].y }
                };

                // Chest, Waist, Hip scans (torso isolation masking applied)
                const chestPx = getSilhouetteWidthAtY(results.segmentationMask, y_chest, w_val, h_val, chestMin, chestMax, torsoLms, isSideView);
                const waistPx = getSilhouetteWidthAtY(results.segmentationMask, y_waist, w_val, h_val, waistMin, waistMax, torsoLms, isSideView);
                const hipPx = getSilhouetteWidthAtY(results.segmentationMask, y_hip_anatomical, w_val, h_val, hipMin, hipMax, torsoLms, isSideView);

                // Arm scans (no torso masking, tight search window around arm joints)
                const y_arm_left_mid = (lms[11].y + lms[13].y) / 2;
                const y_arm_right_mid = (lms[12].y + lms[14].y) / 2;
                const x_arm_left_mid = (lms[11].x + lms[13].x) / 2;
                const x_arm_right_mid = (lms[12].x + lms[14].x) / 2;

                const armLeftMin = (x_arm_left_mid - 0.08) * w_val;
                const armLeftMax = (x_arm_left_mid + 0.08) * w_val;
                const armRightMin = (x_arm_right_mid - 0.08) * w_val;
                const armRightMax = (x_arm_right_mid + 0.08) * w_val;

                const armLeftPx = getArmSilhouetteWidthAtY(
                  results.segmentationMask,
                  { x: lms[11].x, y: lms[11].y },
                  { x: lms[13].x, y: lms[13].y },
                  w_val,
                  h_val,
                  armLeftMin,
                  armLeftMax
                );
                const armRightPx = getArmSilhouetteWidthAtY(
                  results.segmentationMask,
                  { x: lms[12].x, y: lms[12].y },
                  { x: lms[14].x, y: lms[14].y },
                  w_val,
                  h_val,
                  armRightMin,
                  armRightMax
                );

                if (isSideView) {
                  const x_sh_avg = (torsoLms.left_shoulder.x + torsoLms.right_shoulder.x) / 2;
                  const x_hip_avg = (torsoLms.left_hip.x + torsoLms.right_hip.x) / 2;
                  const ls_padded_x = (x_sh_avg - torso_y_span * 0.15) * w_val;
                  const rs_padded_x = (x_sh_avg + torso_y_span * 0.15) * w_val;
                  const lh_padded_x = (x_hip_avg - torso_y_span * 0.15) * w_val;
                  const rh_padded_x = (x_hip_avg + torso_y_span * 0.15) * w_val;

                  console.log(
                    `[Side Torso ROI] x-bounds: Shoulder [${ls_padded_x.toFixed(1)}, ${rs_padded_x.toFixed(1)}], Hip [${lh_padded_x.toFixed(1)}, ${rh_padded_x.toFixed(1)}]`
                  );
                  console.log(
                    `[Side Torso Scan] chest_depth: ${chestPx} px, waist_depth: ${waistPx} px, hip_depth: ${hipPx} px`
                  );
                  console.log(
                    `[Side View - LEFT ARM] shoulder=[${lms[11].x.toFixed(3)}, ${lms[11].y.toFixed(3)}], elbow=[${lms[13].x.toFixed(3)}, ${lms[13].y.toFixed(3)}], midpoint=[${x_arm_left_mid.toFixed(3)}, ${y_arm_left_mid.toFixed(3)}], width=${armLeftPx !== null ? armLeftPx.toFixed(1) : "null"} px`
                  );
                  console.log(
                    `[Side View - RIGHT ARM] shoulder=[${lms[12].x.toFixed(3)}, ${lms[12].y.toFixed(3)}], elbow=[${lms[14].x.toFixed(3)}, ${lms[14].y.toFixed(3)}], midpoint=[${x_arm_right_mid.toFixed(3)}, ${y_arm_right_mid.toFixed(3)}], width=${armRightPx !== null ? armRightPx.toFixed(1) : "null"} px`
                  );
                } else {
                  const dx_sh = torsoLms.right_shoulder.x - torsoLms.left_shoulder.x;
                  const dx_hip = torsoLms.left_hip.x - torsoLms.right_hip.x;
                  const pad_ratio = 0.22;
                  const ls_padded_x = (torsoLms.left_shoulder.x - dx_sh * pad_ratio) * w_val;
                  const rs_padded_x = (torsoLms.right_shoulder.x + dx_sh * pad_ratio) * w_val;
                  const lh_padded_x = (torsoLms.left_hip.x - dx_hip * pad_ratio) * w_val;
                  const rh_padded_x = (torsoLms.right_hip.x + dx_hip * pad_ratio) * w_val;

                  console.log(
                    `[Torso ROI] x-bounds: Shoulder [${ls_padded_x.toFixed(1)}, ${rs_padded_x.toFixed(1)}], Hip [${lh_padded_x.toFixed(1)}, ${rh_padded_x.toFixed(1)}]`
                  );
                  console.log(
                    `[Torso Scan] chest: ${chestPx} px, waist: ${waistPx} px, hip: ${hipPx} px`
                  );
                  console.log(
                    `[Front View - LEFT ARM] shoulder=[${lms[11].x.toFixed(3)}, ${lms[11].y.toFixed(3)}], elbow=[${lms[13].x.toFixed(3)}, ${lms[13].y.toFixed(3)}], midpoint=[${x_arm_left_mid.toFixed(3)}, ${y_arm_left_mid.toFixed(3)}], width=${armLeftPx !== null ? armLeftPx.toFixed(1) : "null"} px`
                  );
                  console.log(
                    `[Front View - RIGHT ARM] shoulder=[${lms[12].x.toFixed(3)}, ${lms[12].y.toFixed(3)}], elbow=[${lms[14].x.toFixed(3)}, ${lms[14].y.toFixed(3)}], midpoint=[${x_arm_right_mid.toFixed(3)}, ${y_arm_right_mid.toFixed(3)}], width=${armRightPx !== null ? armRightPx.toFixed(1) : "null"} px`
                  );
                }

                setSilhouetteChestPx(chestPx);
                setSilhouetteWaistPx(waistPx);
                setSilhouetteHipPx(hipPx);
                setSilhouetteArmLeftPx(armLeftPx);
                setSilhouetteArmRightPx(armRightPx);
              } else {
                setSilhouetteChestPx(null);
                setSilhouetteWaistPx(null);
                setSilhouetteHipPx(null);
                setSilhouetteArmLeftPx(null);
                setSilhouetteArmRightPx(null);
              }
            } else {
              setSilhouetteChestPx(null);
              setSilhouetteWaistPx(null);
              setSilhouetteHipPx(null);
              setSilhouetteArmLeftPx(null);
              setSilhouetteArmRightPx(null);
            }
          } else {
             setLandmarks([]);
             setSilhouetteChestPx(null);
             setSilhouetteWaistPx(null);
             setSilhouetteHipPx(null);
             setSilhouetteArmLeftPx(null);
             setSilhouetteArmRightPx(null);
          }
          canvasCtx.restore();
        }
      });

      poseRef.current = pose;
    }

    reqRef.current = requestAnimationFrame(processFrame);
  }, [processFrame, ready]);

  const detach = React.useCallback(() => {
    cancelAnimationFrame(reqRef.current);
    const canvasCtx = canvasRef.current?.getContext("2d");
    if (canvasCtx && canvasRef.current) {
      canvasCtx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    }
    videoRef.current = null;
    canvasRef.current = null;
    setReady(false);
    setLandmarks([]);
    setSilhouetteChestPx(null);
    setSilhouetteWaistPx(null);
    setSilhouetteHipPx(null);
    setSilhouetteArmLeftPx(null);
    setSilhouetteArmRightPx(null);
  }, []);

  return {
    ready,
    landmarks,
    fps,
    silhouetteChestPx,
    silhouetteWaistPx,
    silhouetteHipPx,
    silhouetteArmLeftPx,
    silhouetteArmRightPx,
    attach,
    detach
  };
}
