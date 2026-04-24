'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@heroui/react';

export function HelloOps() {
  return (
    <Card className="max-w-md mx-auto mt-16">
      <CardHeader>
        <CardTitle>HHPS Ops Console</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm">Phase 5 scaffold. Today board lands in T6.</p>
      </CardContent>
    </Card>
  );
}
