export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-2xl text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
          Web Doc Resolver
        </h1>
        <p className="mt-4 text-lg text-neutral-600 dark:text-neutral-400">
          Resolve queries and URLs into compact, LLM-ready markdown
        </p>
      </div>
    </main>
  );
}