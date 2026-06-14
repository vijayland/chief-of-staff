import { EventList } from "@/components/calendar/EventList";
import { Header } from "@/components/layout/Header";

export default function CalendarPage() {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header
        title="Calendar"
        description="Upcoming events from Google Calendar"
      />
      <div className="flex-1 overflow-hidden">
        <EventList />
      </div>
    </div>
  );
}
