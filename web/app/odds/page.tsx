// The /odds page: tab 5, playoff and championship odds.
import OddsTab from "@/components/OddsTab";
import { PageIntro } from "@/components/Table";

export default function Page() {
  return (
    <>
      <PageIntro title="Playoff odds">
        Each team&apos;s chance to make the playoffs, win each round and take the title, from simulating the rest of
        the season thousands of times.
      </PageIntro>
      <OddsTab />
    </>
  );
}
