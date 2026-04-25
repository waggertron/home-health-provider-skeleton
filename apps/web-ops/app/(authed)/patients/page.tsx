'use client';

import { SimpleList } from '@/components/SimpleList';

interface Patient {
  id: number;
  name: string;
  phone: string;
  address: string;
  required_skill: string;
}

export default function PatientsPage() {
  return (
    <SimpleList<Patient>
      title="Patients"
      queryKey={['patients']}
      path="/api/v1/patients/"
      columns={[
        { header: 'ID', render: (p) => p.id },
        { header: 'Name', render: (p) => p.name },
        { header: 'Skill', render: (p) => p.required_skill },
        { header: 'Address', render: (p) => p.address },
      ]}
      testId="patient-list"
    />
  );
}
