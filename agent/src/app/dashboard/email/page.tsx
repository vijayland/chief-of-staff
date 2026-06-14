import { EmailList } from "@/components/email/EmailList";
import { Header } from "@/components/layout/Header";

export default function EmailPage() {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header
        title="Email"
        description="Your Gmail inbox — synced and searchable"
      />
      <div className="flex-1 overflow-hidden">
        <EmailList />
      </div>
    </div>
  );
}
