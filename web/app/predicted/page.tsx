// The /predicted page: tab 4, predicted standings on a future date.
import PredictedTab from "@/components/PredictedTab";
import { PageIntro } from "@/components/Table";

export default function Page() {
  return (
    <>
      <PageIntro title="Predicted standings">
        Pick a date to see the record the model expects each team to have by then.
      </PageIntro>
      <PredictedTab />
    </>
  );
}
