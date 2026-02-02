import { createSlice } from '@reduxjs/toolkit';
import {
    addConversationMessageThunk,
    createConversationThunk,
    getConversationBranchedThunk,
} from "./conversations";
import { AssistantRole, MockId, MockTitle } from "../utils/constants";
import { postLogoutThunk } from "./auth";

const initialState = {
    id: MockId,
    title: MockTitle,
    conversation_id: MockId,
    root_message: "mock message",
    messages: [],
    active: true,
    parent_version: "mock version",
};

const currentConversationSlice = createSlice({
    name: 'currentConversation',
    initialState,
    reducers: {
        addMessage: (state, action) => {
            const last = state.messages[state.messages.length - 1];
            if (last && last.role === AssistantRole && action.payload.role === AssistantRole) {
                state.messages[state.messages.length - 1] = action.payload;
            } else {
                state.messages.push(action.payload);
            }
        },
        changeTitle: (state, action) => {
            state.title = action.payload;
        },
        startNewConversation: () => initialState,
        setConversation: (state, action) => ({
            ...state,
            ...action.payload,
            messages: action.payload.messages ?? state.messages,
        }),
    },
    extraReducers: (builder) => {
        builder
            .addCase(createConversationThunk.fulfilled, (_, action) => {
                const v = action.payload.versions?.find(v => v.active);
                return v ? { ...v, title: action.payload.title } : initialState;
            })
            .addCase(addConversationMessageThunk.fulfilled, (state, action) => {
                if (action.payload.hidden) return;
                const msg = action.payload.message;
                if (!msg) return;

                const last = state.messages[state.messages.length - 1];
                if (last && last.role === msg.role) {
                    state.messages[state.messages.length - 1] = msg;
                } else {
                    state.messages.push(msg);
                }
            })
            .addCase(getConversationBranchedThunk.fulfilled, (_, action) => {
                const v = action.payload.versions?.find(v => v.active);
                return v ? { ...v, title: action.payload.title } : initialState;
            })
            .addCase(postLogoutThunk.fulfilled, () => initialState);
    }
});

export const { addMessage, changeTitle, startNewConversation, setConversation } =
    currentConversationSlice.actions;

export default currentConversationSlice.reducer;
