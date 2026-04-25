'use client';

import { SimpleList } from '@/components/SimpleList';
import type { Clinician } from '@/hooks/useTodayBoard';

export default function CliniciansPage() {
  return (
    <SimpleList<Clinician>
      title="Clinicians"
      queryKey={['clinicians']}
      path="/api/v1/clinicians/"
      columns={[
        { header: 'ID', render: (c) => c.id },
        { header: 'Credential', render: (c) => c.credential },
        {
          header: 'Home',
          render: (c) => `${c.home_lat.toFixed(3)}, ${c.home_lon.toFixed(3)}`,
        },
      ]}
      testId="clinician-list"
    />
  );
}
