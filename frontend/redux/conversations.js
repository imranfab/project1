import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { setStreaming } from "./streaming";
import { setLoading } from "./loading";
import { postLogoutThunk } from "./auth";
import { axiosInstance } from "../api/axios";



export const fetchConversationsThunk = createAsyncThunk(
    'conversations/fetch',
    async (_, thunkAPI) => {
        try {
            const response = await axiosInstance.get(`/chat/conversations_branched/`);
            return response.data.map(c => ({ ...c, active: false }));
        } catch (error) {
            return thunkAPI.rejectWithValue({ error: error.message });
        } finally {
            thunkAPI.dispatch(setLoading(false));
        }
    }
);

export const createConversationThunk = createAsyncThunk(
    'conversations/create',
    async ({ title, messages }) => {
        const response = await axiosInstance.post(
            `/chat/conversations/add/`,
            { title, messages }
        );
        return { ...response.data, active: true };
    }
);

export const changeConversationTitleThunk = createAsyncThunk(
    'conversations/changeTitle',
    async ({ id, newTitle }, thunkAPI) => {
        try {
            await axiosInstance.put(
                `/chat/conversations/${id}/change_title/`,
                { title: newTitle }
            );
            return { id, title: newTitle };
        } catch (error) {
            return thunkAPI.rejectWithValue({ error: error.message });
        }
    }
);

export const deleteConversationThunk = createAsyncThunk(
    'conversations/delete',
    async ({ id }, thunkAPI) => {
        try {
            await axiosInstance.put(
                `/chat/conversations/${id}/delete/`,
                {}
            );
            return id;
        } catch (error) {
            return thunkAPI.rejectWithValue({ error: error.message });
        }
    }
);

export const addConversationMessageThunk = createAsyncThunk(
    'conversations/addMessage',
    async ({ conversationId, message, hidden }) => {
        const response = await axiosInstance.post(
            `/chat/conversations/${conversationId}/add_message/`,
            { role: message.role, content: message.content }
        );
        return { ...response.data, hidden };
    }
);

export const addConversationVersionThunk = createAsyncThunk(
    'conversations/addVersion',
    async ({ conversationId, rootMessageId }) => {
        const response = await axiosInstance.post(
            `/chat/conversations/${conversationId}/add_version/`,
            { root_message_id: rootMessageId }
        );
        return response.data;
    }
);

export const getConversationBranchedThunk = createAsyncThunk(
    'conversations/getBranched',
    async ({ conversationId }) => {
        const response = await axiosInstance.get(
            `/chat/conversation_branched/${conversationId}/`
        );
        return { ...response.data, active: true };
    }
);

export const switchConversationVersionThunk = createAsyncThunk(
    'conversations/switchVersion',
    async ({ conversationId, versionId }) => {
        await axiosInstance.put(
            `/chat/conversations/${conversationId}/switch_version/${versionId}/`,
            {}
        );
        return { conversationId, versionId };
    }
);

/* ===================== SLICE ===================== */

const allConversationsSlice = createSlice({
    name: 'allConversations',
    initialState: [],
    reducers: {
        setActiveConversation: (state, action) => {
            const id = action.payload;
            state.forEach(conversation => {
                conversation.active = conversation.id === id;
            });
        }
    },
    extraReducers: (builder) => {
        builder
            .addCase(fetchConversationsThunk.fulfilled, (_, action) => action.payload)

            .addCase(createConversationThunk.fulfilled, (state, action) => {
                state.forEach(c => c.active = false);
                state.push(action.payload);
            })

            .addCase(changeConversationTitleThunk.fulfilled, (state, action) => {
                const convo = state.find(c => c.id === action.payload.id);
                if (convo) convo.title = action.payload.title;
            })

            .addCase(deleteConversationThunk.fulfilled, (state, action) => {
                return state.filter(c => c.id !== action.payload);
            })

            .addCase(addConversationMessageThunk.fulfilled, (state, action) => {
                const { conversation_id, message } = action.payload;
                const conversation = state.find(c => c.id === conversation_id);
                if (!conversation || !conversation.versions?.length) return;

                const version =
                    conversation.versions.find(v => v.id === conversation.active_version) ||
                    conversation.versions.find(v => v.active);

                if (!version || !Array.isArray(version.messages)) return;

                version.messages.push(message);
            })

            .addCase(addConversationVersionThunk.fulfilled, (state, action) => {
                const conversation = state.find(c => c.id === action.payload.conversation_id);
                if (!conversation) return;

                conversation.versions.forEach(v => v.active = false);
                conversation.versions.push({ ...action.payload, active: true });
            })

            .addCase(getConversationBranchedThunk.fulfilled, (state, action) => {
                const index = state.findIndex(c => c.id === action.payload.id);
                if (index === -1) return;
                state[index] = action.payload;
            })

            .addCase(switchConversationVersionThunk.fulfilled, (state, action) => {
                const conversation = state.find(c => c.id === action.payload.conversationId);
                if (!conversation) return;

                conversation.versions.forEach(v => v.active = false);
                const version = conversation.versions.find(v => v.id === action.payload.versionId);
                if (version) version.active = true;
            })

            .addCase(setStreaming, (state) => {
                const convo = state.find(c => c.active);
                if (convo) convo.modified_at = new Date().toISOString();
            })

            .addCase(postLogoutThunk.fulfilled, () => []);
    }
});



export const { setActiveConversation } = allConversationsSlice.actions;
export default allConversationsSlice.reducer;
