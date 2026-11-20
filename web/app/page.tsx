// The home page ("/") is the first tab, Results, just like the Streamlit app.
// The title and one-line description (PageIntro) are drawn here, outside the tab, so they
// show up instantly while the tab is still loading its data.
import ResultsTab from "@/components/ResultsTab";
import { PageIntro } from "@/components/Table";

export default function ResultsPage() {
  return (
    <>
      <PageIntro title="Results">Every finished game this season, newest first. The winner is in bold.</PageIntro>
      <ResultsTab />
    </>
  );
}
