// The /standings page: tab 3, the current standings.
import StandingsTable from "@/components/StandingsTable";
import { PageIntro } from "@/components/Table";

export default function Page() {
  return (
    <>
      <PageIntro title="Standings">Where every team stands today, by conference.</PageIntro>
      <StandingsTable />
    </>
  );
}
