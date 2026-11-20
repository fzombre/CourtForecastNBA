// The /upcoming page: tab 2, upcoming games and the model's picks.
import { PageIntro } from "@/components/Table";
import UpcomingTab from "@/components/UpcomingTab";

export default function Page() {
  return (
    <>
      <PageIntro title="Upcoming & picks">
        Every game left on the schedule, with each team&apos;s chance to win. The gold side of each bar is the
        model&apos;s pick.
      </PageIntro>
      <UpcomingTab />
    </>
  );
}
