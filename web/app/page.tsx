import StandingsTable from "@/components/StandingsTable";

export default function Home() {
  return (
    <main className="mx-auto max-w-5xl p-8">
      <h1 className="mb-6 text-3xl font-bold">CourtForecastNBA</h1>
      <StandingsTable />
    </main>
  );
}
