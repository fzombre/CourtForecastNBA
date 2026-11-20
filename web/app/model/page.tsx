// The /model page: tab 6, how the model is doing.
import ModelTab from "@/components/ModelTab";
import { PageIntro } from "@/components/Table";

export default function Page() {
  return (
    <>
      <PageIntro title="Model">How often the model picks the winner, what it has learned, and how it rates every team.</PageIntro>
      <ModelTab />
    </>
  );
}
