import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { ApiService, SubscriptionPlan, UsageInfo } from '../../services/api';

interface SubscriptionState {
  currentSubscription: UsageInfo | null;
  subscriptionPlans: SubscriptionPlan[];
  usageHistory: any[] | null;
  loading: boolean;
  upgrading: boolean;
  error: string | null;
}

const initialState: SubscriptionState = {
  currentSubscription: null,
  subscriptionPlans: [],
  usageHistory: null,
  loading: false,
  upgrading: false,
  error: null,
};

// Async thunks
export const loadSubscriptionData = createAsyncThunk(
  'subscription/loadData',
  async () => {
    const [subscription, plans, usage] = await Promise.all([
      ApiService.getCurrentSubscription(),
      ApiService.getSubscriptionPlans(),
      ApiService.getUsageHistory(30)
    ]);
    
    return { subscription, plans, usage };
  }
);

export const upgradeSubscription = createAsyncThunk(
  'subscription/upgrade',
  async (planId: string) => {
    await ApiService.upgradeSubscription(planId);
    // Return updated subscription data
    return await ApiService.getCurrentSubscription();
  }
);

const subscriptionSlice = createSlice({
  name: 'subscription',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Load subscription data
      .addCase(loadSubscriptionData.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(loadSubscriptionData.fulfilled, (state, action) => {
        state.loading = false;
        state.currentSubscription = action.payload.subscription;
        state.subscriptionPlans = action.payload.plans;
        state.usageHistory = action.payload.usage;
      })
      .addCase(loadSubscriptionData.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to load subscription data';
      })
      
      // Upgrade subscription
      .addCase(upgradeSubscription.pending, (state) => {
        state.upgrading = true;
        state.error = null;
      })
      .addCase(upgradeSubscription.fulfilled, (state, action) => {
        state.upgrading = false;
        state.currentSubscription = action.payload;
      })
      .addCase(upgradeSubscription.rejected, (state, action) => {
        state.upgrading = false;
        state.error = action.error.message || 'Failed to upgrade subscription';
      });
  },
});

export const { clearError } = subscriptionSlice.actions;
export default subscriptionSlice.reducer;
