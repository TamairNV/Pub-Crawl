export interface WheelItem {
  id: string;
  wheel_id: string;
  label: string;
  description?: string | null;
  requires_completion: boolean;
  effect_type: 'add_points' | 'deduct_team' | 'steal_team' | 'none';
  points: number;
  colour: string;
  sort_order?: number;
}

export interface MiniWheel {
  id: string;
  event_id: string;
  name: string;
  description?: string | null;
  sort_order?: number;
  items: WheelItem[];
}

export interface PlayerTask {
  id: string;
  event_id: string;
  user_id: string;
  user_name?: string;
  user_team_id?: string;
  user_team_name?: string;
  user_team_colour?: string;
  wheel_id?: string | null;
  wheel_name?: string | null;
  wheel_item_id?: string | null;
  title: string;
  description?: string | null;
  status: 'pending' | 'ready_to_spin' | 'awaiting_target' | 'completed' | 'cancelled';
  reward_type: 'spin_wheel' | 'add_points' | 'deduct_team' | 'steal_team' | 'none';
  reward_points: number;
  reward_wheel_id?: string | null;
  reward_wheel_name?: string | null;
  spun_item_id?: string | null;
  spun_label?: string | null;
  spun_effect_type?: string | null;
  spun_points?: number | null;
  target_team_id?: string | null;
  target_team_name?: string | null;
  player_claimed_done: boolean;
  result_summary?: string | null;
  created_at?: string;
}

export interface EventAward {
  id: string;
  event_id: string;
  name: string;
  description?: string | null;
  target_type: 'player' | 'team' | 'either';
  sort_order?: number;
}

export function formatRewardBadge(
  rewardType: string,
  points: number,
  wheelName?: string | null
): string {
  const pts = Number(points || 0);
  if (rewardType === 'spin_wheel') {
    return wheelName ? `Spin: ${wheelName}` : 'Spin the Wheel';
  }
  if (rewardType === 'add_points') {
    return `${pts >= 0 ? '+' : ''}${pts} pts`;
  }
  if (rewardType === 'deduct_team') {
    return `-${Math.abs(pts)} pts to another team`;
  }
  if (rewardType === 'steal_team') {
    return `Steal ${Math.abs(pts)} pts from another team`;
  }
  return 'Fun dare';
}
