"use client";

import {
  Calendar,
  Clock,
  ExternalLink,
  MapPin,
  Trash2,
  Users,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import type { CalendarEvent } from "@/types";

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}
function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString([], {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}
function formatDuration(start: string, end: string) {
  const mins = (new Date(end).getTime() - new Date(start).getTime()) / 60000;
  if (mins < 60) return `${mins}m`;
  return `${Math.floor(mins / 60)}h${mins % 60 ? ` ${mins % 60}m` : ""}`;
}
function groupByDate(events: CalendarEvent[]) {
  const map: Record<string, CalendarEvent[]> = {};
  for (const e of events) {
    const key = new Date(e.start).toDateString();
    if (!map[key]) map[key] = [];
    map[key].push(e);
  }
  return map;
}

function EventSkeleton() {
  return (
    <div className="flex gap-3 p-3.5 rounded-lg border border-border bg-white">
      <div className="w-1 rounded-full bg-border shrink-0 self-stretch min-h-10" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-3.5 w-3/5" />
        <Skeleton className="h-2.5 w-2/5" />
      </div>
    </div>
  );
}

export function EventList() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [daysAhead, setDaysAhead] = useState(7);

  const load = useCallback(async (days: number) => {
    setLoading(true);
    try {
      const data = await api.calendar.events(days);
      setEvents(data);
    } catch {
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(daysAhead);
  }, [daysAhead, load]);

  async function deleteEvent(id: string) {
    await api.calendar.delete(id);
    setEvents((prev) => prev.filter((e) => e.id !== id));
  }

  const grouped = groupByDate(events);

  return (
    <div className="flex flex-col h-full">
      {/* Controls */}
      <div className="px-6 py-3 border-b border-border flex items-center gap-2 bg-white">
        <span className="text-xs font-medium text-text-muted mr-1">Show:</span>
        {[7, 14, 30].map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => setDaysAhead(d)}
            className={`px-3 py-1.5 text-xs font-medium rounded-full transition-all
              ${
                daysAhead === d
                  ? "bg-text-primary text-white shadow-sm"
                  : "text-text-secondary hover:bg-surface-hover"
              }`}
          >
            {d} days
          </button>
        ))}
      </div>

      {/* Events */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {loading ? (
          <div className="space-y-6">
            {[1, 2].map((g) => (
              <div key={g}>
                <Skeleton className="h-3 w-32 mb-3" />
                <div className="space-y-2">
                  {Array.from({ length: g === 1 ? 2 : 1 }, (_, i) => (
                    <EventSkeleton key={`esk-${g}-${i}`} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : events.length === 0 ? (
          <div className="flex flex-col items-center justify-center pt-20 gap-3">
            <div className="w-12 h-12 rounded-2xl bg-surface-sidebar flex items-center justify-center">
              <Calendar className="w-6 h-6 text-text-muted" />
            </div>
            <p className="text-sm font-medium text-text-primary">All clear!</p>
            <p className="text-xs text-text-muted">
              No events in the next {daysAhead} days
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(grouped).map(([dateStr, dayEvents]) => (
              <div key={dateStr}>
                <p className="text-[11px] font-bold text-text-muted uppercase tracking-widest mb-2.5">
                  {formatDate(dayEvents[0].start)}
                </p>
                <div className="space-y-2">
                  {dayEvents.map((event) => (
                    <div
                      key={event.id}
                      className="flex gap-3 p-3.5 rounded-lg border border-border
                        bg-white hover:shadow-sm transition-all group"
                    >
                      <div className="w-1 rounded-full bg-accent shrink-0 self-stretch" />

                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-semibold text-text-primary leading-snug">
                            {event.title}
                          </p>
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                            {event.html_link && (
                              <a
                                href={event.html_link}
                                target="_blank"
                                rel="noreferrer"
                                className="p-1.5 rounded hover:bg-surface-hover text-text-muted hover:text-accent transition-colors"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
                              </a>
                            )}
                            <button
                              type="button"
                              onClick={() => deleteEvent(event.id)}
                              className="p-1.5 rounded hover:bg-danger-light text-text-muted hover:text-danger transition-colors"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-3 mt-1.5">
                          <span className="flex items-center gap-1 text-xs text-text-secondary">
                            <Clock className="w-3 h-3 text-text-muted" />
                            {formatTime(event.start)} ·{" "}
                            {formatDuration(event.start, event.end)}
                          </span>
                          {event.location && (
                            <span className="flex items-center gap-1 text-xs text-text-secondary">
                              <MapPin className="w-3 h-3 text-text-muted" />{" "}
                              {event.location}
                            </span>
                          )}
                          {event.attendees.length > 0 && (
                            <span className="flex items-center gap-1 text-xs text-text-secondary">
                              <Users className="w-3 h-3 text-text-muted" />
                              {event.attendees.length} attendee
                              {event.attendees.length > 1 ? "s" : ""}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
