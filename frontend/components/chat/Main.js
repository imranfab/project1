import React, { useCallback, useEffect, useRef, useState } from 'react';
import styles from "../../styles/chat/Main.module.css";
import { postChatConversation, postChatTitle } from "../../api/gpt";
import Conversation from "./Conversation";
import ChoiceButton from "./ModelButton";
import { useDispatch, useSelector } from "react-redux";
import { addMessage, changeTitle, setConversation } from "../../redux/currentConversation";
import {
    addConversationMessageThunk,
    addConversationVersionThunk,
    createConversationThunk,
    getConversationBranchedThunk,
} from "../../redux/conversations";
import { setStreaming } from "../../redux/streaming";
import {
    AssistantRole,
    GPT35,
    MessageTypes,
    MockTitle,
    UserRole
} from "../../utils/constants";
import { generateMockId } from "../../utils/functions";
import { ControlButtons } from "./ControlButtons";

const Chat = () => {
    const currVersion = useSelector(state => state.currentConversation);
    const isStreaming = useSelector(state => state.streaming);
    const dispatch = useDispatch();

    const chatContainerRef = useRef(null);
    const inputRef = useRef(null);
    const abortController = useRef(new AbortController());

    const [userInput, setUserInput] = useState('');
    const [canStop, setCanStop] = useState(false);
    const [canRegenerate, setCanRegenerate] = useState(false);
    const [versionUpdatePromise, setVersionUpdatePromise] = useState(null);
    const [error, setError] = useState(null);
    const [chosenModel, setChosenModel] = useState(GPT35);



    useEffect(() => {
        const el = chatContainerRef.current;
        if (el) el.scrollTop = el.scrollHeight;

        const msgs = currVersion.messages || [];
        const lastMessage = msgs[msgs.length - 1];
        const hasUser = msgs.some(m => m.role === UserRole);
        const hasAssistant =
            lastMessage &&
            lastMessage.role === AssistantRole &&
            lastMessage.content !== '';

        setCanRegenerate(hasUser && hasAssistant && !isStreaming);
        setCanStop(isStreaming && hasAssistant);

        if (msgs.length === 2 && !isStreaming && currVersion.title === MockTitle) {
            generateTitle().catch(console.error);
        }
    }, [currVersion, isStreaming]);



    const updateInputHeight = () => {
        if (!inputRef.current) return;
        inputRef.current.style.height = "auto";
        inputRef.current.style.height = `${inputRef.current.scrollHeight}px`;
    };

    const generateTitle = async () => {
        const lastTwo = currVersion.messages.slice(-2);
        const userMsg = lastTwo.find(m => m.role === UserRole);
        const assistantMsg = lastTwo.find(m => m.role === AssistantRole);
        if (!userMsg || !assistantMsg) return;

        let title = "Conversation";
        try {
            title = await postChatTitle({
                user_question: userMsg.content,
                chatbot_response: assistantMsg.content,
            });
        } catch {}

        dispatch(changeTitle(title));
        dispatch(createConversationThunk({ title, messages: currVersion.messages }));
    };



    const generateResponse = async (
        prompt = userInput,
        messageType = MessageTypes.UserMessage,
        messageId = null
    ) => {
        let newConversationMessages = [];
        let newMessage;

        switch (messageType) {
            case MessageTypes.UserMessage:
                newMessage = { role: UserRole, content: prompt, id: generateMockId() };
                newConversationMessages = [...currVersion.messages, newMessage];
                addMessageToConversation(prompt, UserRole);
                break;

            default:
                return;
        }

        dispatch(addMessage(newMessage));
        setUserInput('');
        updateInputHeight();
        dispatch(setStreaming(true));

        try {
            const reader = await postChatConversation(
                newConversationMessages.map(m => ({ role: m.role, content: m.content })),
                chosenModel,
                { signal: abortController.current.signal }
            );

            const decoder = new TextDecoder();
            let data = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                data += decoder.decode(value, { stream: true });
            }

            dispatch(addMessage({
                role: AssistantRole,
                content: data,
                id: generateMockId()
            }));

        } catch (err) {
            if (err.name !== "AbortError") {
                setError(err.message);
            }
        } finally {
            dispatch(setStreaming(false));
        }
    };

    const addMessageToConversation = (message, role) => {
        if (!currVersion.conversation_id || currVersion.title === MockTitle) return;
        return dispatch(addConversationMessageThunk({
            conversationId: currVersion.conversation_id,
            message: { role, content: message },
        }));
    };


    return (
        <div className={styles.chatContainer} ref={chatContainerRef}>
            <div className={styles.conversationContainer}>
                <Conversation
                    messages={currVersion.messages}
                    regenerateUserResponse={() => {}}
                    error={error}
                />
            </div>

            <div className={styles.chatControlContainer}>
                <div className={styles.chatControlInner}>

                    <ChoiceButton
                        disabled={isStreaming}
                        chosenModel={chosenModel}
                        onChoice={setChosenModel}
                    />

                    <div className={styles.chatInputContainer}>
                        <textarea
                            ref={inputRef}
                            placeholder="Type a message here..."
                            value={userInput}
                            onChange={e => {
                                setUserInput(e.target.value);
                                updateInputHeight();
                            }}
                            onKeyDown={e => {
                                if (e.key === "Enter" && !e.shiftKey) {
                                    e.preventDefault();
                                    generateResponse(userInput);
                                }
                            }}
                            rows={1}
                        />
                    </div>

                    <ControlButtons
                        generateProps={{
                            onClick: () => generateResponse(userInput),
                            disabled: !userInput || isStreaming,
                        }}
                        stopProps={{ disabled: true }}
                        regenerateProps={{ disabled: true }}
                    />

                </div>
            </div>
        </div>
    );
};

export default Chat;
