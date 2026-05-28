import * as React from "react";
import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Loader2, Save } from "lucide-react";
import { GlassCard, SectionHeader } from "@/components/brand/GlassCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { profileApi, type Profile } from "@/lib/api/profile";

export const Route = createFileRoute("/_app/profile")({
  component: ProfilePage,
});

function ProfilePage() {
  const qc = useQueryClient();
  const existing = useQuery({ queryKey: ["profile"], queryFn: profileApi.get, retry: false });
  const [form, setForm] = React.useState<Profile>({});
  const [initialized, setInitialized] = React.useState(false);

  React.useEffect(() => {
    if (existing.data && !initialized) {
      setForm(existing.data);
      setInitialized(true);
    } else if (existing.isError && !initialized) {
      setInitialized(true);
    }
  }, [existing.data, existing.isError, initialized]);

  const hasProfile = !!existing.data;

  const save = useMutation({
    mutationFn: (p: Profile) => (hasProfile ? profileApi.update(p) : profileApi.create(p)),
    onSuccess: (data) => {
      qc.setQueryData(["profile"], data);
      toast.success("Profile saved");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const cleaned: Profile = {
      ...form,
      age: form.age !== undefined && String(form.age) !== "" ? Number(form.age) : undefined,
      height_cm: form.height_cm !== undefined && String(form.height_cm) !== "" ? Number(form.height_cm) : undefined,
      weight_kg: form.weight_kg !== undefined && String(form.weight_kg) !== "" ? Number(form.weight_kg) : undefined,
    };
    save.mutate(cleaned);
  };

  return (
    <div>
      <SectionHeader title="Profile" subtitle={hasProfile ? "Manage your profile and fitness settings" : "Set up your profile to personalize your plan."} />

      <GlassCard>
        {existing.isLoading ? (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-16 animate-pulse rounded-lg bg-muted/20" />)}
          </div>
        ) : (
          <form onSubmit={submit} className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {/* Full Name */}
            <div className="space-y-1.5">
              <Label htmlFor="full_name">Full Name</Label>
              <Input
                id="full_name"
                placeholder="Alex Doe"
                value={(form.full_name as string) ?? ""}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                required
              />
            </div>

            {/* Age */}
            <div className="space-y-1.5">
              <Label htmlFor="age">Age</Label>
              <Input
                id="age"
                type="number"
                placeholder="27"
                value={form.age ?? ""}
                onChange={(e) => setForm({ ...form, age: e.target.value ? Number(e.target.value) : undefined })}
                required
              />
            </div>

            {/* Height (cm) */}
            <div className="space-y-1.5">
              <Label htmlFor="height_cm">Height (cm)</Label>
              <Input
                id="height_cm"
                type="number"
                placeholder="175"
                value={form.height_cm ?? ""}
                onChange={(e) => setForm({ ...form, height_cm: e.target.value ? Number(e.target.value) : undefined })}
                required
              />
            </div>

            {/* Weight (kg) */}
            <div className="space-y-1.5">
              <Label htmlFor="weight_kg">Weight (kg)</Label>
              <Input
                id="weight_kg"
                type="number"
                placeholder="72"
                value={form.weight_kg ?? ""}
                onChange={(e) => setForm({ ...form, weight_kg: e.target.value ? Number(e.target.value) : undefined })}
                required
              />
            </div>

            {/* Gender / Sex */}
            <div className="space-y-1.5">
              <Label htmlFor="gender">Gender</Label>
              <Select
                value={(form.gender as string) ?? ""}
                onValueChange={(val) => setForm({ ...form, gender: val })}
              >
                <SelectTrigger id="gender" className="w-full">
                  <SelectValue placeholder="Select gender" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="male">Male</SelectItem>
                  <SelectItem value="female">Female</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                  <SelectItem value="prefer_not_to_say">Prefer not to say</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Activity Level */}
            <div className="space-y-1.5">
              <Label htmlFor="activity_level">Activity Level</Label>
              <Select
                value={(form.activity_level as string) ?? ""}
                onValueChange={(val) => setForm({ ...form, activity_level: val })}
              >
                <SelectTrigger id="activity_level" className="w-full">
                  <SelectValue placeholder="Select activity level" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="sedentary">Sedentary (Little to no exercise)</SelectItem>
                  <SelectItem value="light">Light (Exercise 1-3 times/week)</SelectItem>
                  <SelectItem value="moderate">Moderate (Exercise 3-5 times/week)</SelectItem>
                  <SelectItem value="active">Active (Exercise 6-7 times/week)</SelectItem>
                  <SelectItem value="very_active">Very Active (Intense training/physical job)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Fitness Goal */}
            <div className="space-y-1.5">
              <Label htmlFor="goal">Fitness Goal</Label>
              <Select
                value={(form.goal as string) ?? ""}
                onValueChange={(val) => setForm({ ...form, goal: val })}
              >
                <SelectTrigger id="goal" className="w-full">
                  <SelectValue placeholder="Select fitness goal" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="lose_fat">Lose Fat</SelectItem>
                  <SelectItem value="maintain">Maintain Weight</SelectItem>
                  <SelectItem value="lean_bulk">Lean Bulk</SelectItem>
                  <SelectItem value="build_muscle">Build Muscle</SelectItem>
                  <SelectItem value="recomposition">Body Recomposition</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Dietary Preference */}
            <div className="space-y-1.5">
              <Label htmlFor="dietary_pref">Dietary Preference</Label>
              <Select
                value={(form.dietary_pref as string) ?? ""}
                onValueChange={(val) => setForm({ ...form, dietary_pref: val })}
              >
                <SelectTrigger id="dietary_pref" className="w-full">
                  <SelectValue placeholder="Select dietary preference" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="non_vegetarian">Omnivore (Non-Vegetarian)</SelectItem>
                  <SelectItem value="vegetarian">Vegetarian</SelectItem>
                  <SelectItem value="vegan">Vegan</SelectItem>
                  <SelectItem value="eggetarian">Eggetarian</SelectItem>
                  <SelectItem value="pescatarian">Pescatarian</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="md:col-span-2">
              <Button type="submit" disabled={save.isPending} className="bg-primary text-primary-foreground hover:bg-primary/90 mt-2">
                {save.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                {hasProfile ? "Update Profile" : "Create Profile"}
              </Button>
            </div>
          </form>
        )}
      </GlassCard>
    </div>
  );
}
