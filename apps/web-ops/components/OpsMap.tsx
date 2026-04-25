'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@heroui/react';
import { useClinicianPositions, type ClinicianPosition } from '@/hooks/useClinicianPositions';

// LA Basin bounding box used to map lat/lon → SVG x/y.
const BOUNDS = {
  latMin: 33.85,
  latMax: 34.25,
  lonMin: -118.6,
  lonMax: -117.9,
};

const VIEW = { width: 600, height: 360 };

interface OpsMapProps {
  tenantId: number | undefined;
}

function project(lat: number, lon: number): { x: number; y: number } {
  const x = ((lon - BOUNDS.lonMin) / (BOUNDS.lonMax - BOUNDS.lonMin)) * VIEW.width;
  const y = (1 - (lat - BOUNDS.latMin) / (BOUNDS.latMax - BOUNDS.latMin)) * VIEW.height;
  return { x, y };
}

export function OpsMap({ tenantId }: OpsMapProps) {
  const positions = useClinicianPositions(tenantId);
  const positionRows = positions.data ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>LA Basin · live</CardTitle>
      </CardHeader>
      <CardContent>
        <svg
          role="img"
          aria-label="Operations map"
          viewBox={`0 0 ${VIEW.width} ${VIEW.height}`}
          className="w-full bg-slate-950 border border-slate-800 rounded"
          data-testid="ops-map"
        >
          {/* Subtle grid for visual scale */}
          <defs>
            <pattern id="grid" width="60" height="36" patternUnits="userSpaceOnUse">
              <path d="M 60 0 L 0 0 0 36" fill="none" stroke="#1e293b" strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Clinician markers */}
          {positionRows.map((p: ClinicianPosition) => {
            const { x, y } = project(p.lat, p.lon);
            return (
              <g key={`c-${p.clinician}`} data-testid={`clinician-marker-${p.clinician}`}>
                <circle cx={x} cy={y} r={8} fill="#06b6d4" opacity="0.6" />
                <circle cx={x} cy={y} r={3} fill="#67e8f9" />
              </g>
            );
          })}
        </svg>
        <p className="text-xs opacity-50 mt-2">
          {positionRows.length} clinician{positionRows.length === 1 ? '' : 's'} on the map
        </p>
      </CardContent>
    </Card>
  );
}
