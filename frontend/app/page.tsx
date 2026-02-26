import { MatchInput } from "@/components/MatchInput";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 py-12">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-white mb-2">Match analysis</h1>
        <p className="text-zinc-400 text-lg">Enter the teams you want to analyze</p>
        <p className="text-zinc-500 text-sm mt-1 max-w-md mx-auto">
          Our AI is connected to football news and crosses millions of data points for each prediction.
        </p>
      </div>
      <MatchInput />
    </main>
  );
}
