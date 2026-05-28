import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, RefreshCw, Flame } from "lucide-react";
import { GlassCard, SectionHeader, StatTile, EmptyState } from "@/components/brand/GlassCard";
import { Button } from "@/components/ui/button";
import { dietApi } from "@/lib/api/diet";

export const Route = createFileRoute("/_app/diet")({
  component: DietPage,
});

function DietPage() {
  const qc = useQueryClient();
  const diet = useQuery({ queryKey: ["diet"], queryFn: dietApi.get, retry: false });
  const refresh = useMutation({
    mutationFn: dietApi.refresh,
    onSuccess: (data) => {
      qc.setQueryData(["diet"], data);
      toast.success("Diet plan refreshed");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div>
      <SectionHeader
        title="Adaptive diet"
        subtitle="Macros and meals tailored to your body and goals."
        action={
          <Button onClick={() => refresh.mutate()} disabled={refresh.isPending} className="bg-primary text-primary-foreground hover:bg-primary/90">
            {refresh.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            Refresh plan
          </Button>
        }
      />

      {diet.isLoading ? (
        <div className="glass h-40 animate-pulse rounded-2xl" />
      ) : diet.data ? (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatTile label="Calories" value={diet.data.calories ?? "—"} unit="kcal" accent />
            <StatTile label="Protein" value={diet.data.protein_g ?? "—"} unit="g" />
            <StatTile label="Carbs" value={diet.data.carbs_g ?? "—"} unit="g" />
            <StatTile label="Fats" value={diet.data.fats_g ?? "—"} unit="g" />
          </div>

          <div className="mt-8 space-y-4">
            <h2 className="text-sm uppercase tracking-wider text-muted-foreground">Today's meals</h2>
            {!Array.isArray(diet.data.meals) || diet.data.meals.length === 0 ? (
              <p className="text-sm text-muted-foreground">Meal breakdown not provided.</p>
            ) : (
              <div className="grid gap-3 md:grid-cols-2">
                {diet.data.meals.map((m, i) => (
                  <GlassCard key={i}>
                    <div className="flex items-center justify-between">
                      <h3 className="font-display font-semibold">{m?.name}</h3>
                      {m?.calories ? (
                        <span className="inline-flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-xs font-mono-data text-primary">
                          <Flame className="h-3 w-3" /> {m.calories} kcal
                        </span>
                      ) : null}
                    </div>
                    <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
                      {m && Array.isArray(m.items) ? (
                        m.items.map((it, j) => <li key={j}>• {it}</li>)
                      ) : m && Array.isArray((m as any).foods) ? (
                        ((m as any).foods as any[]).map((it, j) => <li key={j}>• {it}</li>)
                      ) : (
                        <li>No items listed</li>
                      )}
                    </ul>
                  </GlassCard>
                ))}
              </div>
            )}
          </div>
        </>
      ) : (
        <EmptyState
          title="No diet plan yet"
          description="Generate your first plan based on your profile and recent measurements."
          action={<Button onClick={() => refresh.mutate()} disabled={refresh.isPending} className="bg-primary text-primary-foreground hover:bg-primary/90">Generate plan</Button>}
        />
      )}
    </div>
  );
}
