// The /mvp page: the MVP race. Today's ladder and each contender's chance to win the award.
import MvpTab from "@/components/MvpTab";
import { PageIntro } from "@/components/Table";

export default function Page() {
  return (
    <>
      <PageIntro title="MVP race">
        Who would win MVP if the season ended today, and who is most likely to win it, from a model trained on 30
        years of MVP votes and the same simulated seasons as the playoff odds.
      </PageIntro>
      <MvpTab />
    </>
  );
}
