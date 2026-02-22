export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-xl border border-dashed border-gray-800 bg-gray-900 p-8 text-center">
      <h3 className="mb-2 text-lg text-gray-100">{title}</h3>
      <p className="text-sm text-gray-400">{description}</p>
    </div>
  );
}
