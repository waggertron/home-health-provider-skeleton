'use client';

import { SimpleList } from '@/components/SimpleList';

interface Sms {
  id: number;
  patient: number;
  visit: number | null;
  template: string;
  body: string;
  status: string;
  created_at: string;
  delivered_at: string | null;
}

export default function SmsPage() {
  return (
    <SimpleList<Sms>
      title="SMS log"
      queryKey={['sms']}
      path="/api/v1/sms/"
      columns={[
        { header: 'ID', render: (s) => s.id },
        { header: 'Template', render: (s) => s.template },
        { header: 'Status', render: (s) => s.status },
        { header: 'Body', render: (s) => s.body.slice(0, 80) },
      ]}
      testId="sms-list"
    />
  );
}
