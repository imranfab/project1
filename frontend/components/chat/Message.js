import React, { useCallback, useEffect, useState } from 'react';
import styles from "../../styles/chat/Message.module.css";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { darcula } from "react-syntax-highlighter/dist/cjs/styles/prism";
import { useDispatch, useSelector } from "react-redux";
import { switchConversationVersionThunk } from "../../redux/conversations";
import { setConversation } from "../../redux/currentConversation";
import { AdditionalInfo } from "./MessageAdditionalInfo";

const Message = ({ message, regenerateUserResponse }) => {
    if (!message) return null;

    const isUser = message.role === 'user';
    const classRole = isUser ? styles.user : styles.assistant;
    const versions = Array.isArray(message.versions) ? message.versions : [];

    const dispatch = useDispatch();
    const currVersion = useSelector(state => state.currentConversation);
    const currConversation = useSelector(
        state => state.allConversations.find(c => c.id === currVersion?.conversation_id)
    );
    const isStreaming = useSelector(state => state.streaming);

    const switchVersion = useCallback((idx, dir) => {
        if (!currConversation || !versions[idx]) return;
        const target = versions[dir === 'left' ? idx - 1 : idx + 1];
        if (!target) return;

        dispatch(switchConversationVersionThunk({
            conversationId: currConversation.id,
            versionId: target.id
        }));

        const newVersion = currConversation.versions.find(v => v.id === target.id);
        if (newVersion) {
            dispatch(setConversation({ ...newVersion, title: currConversation.title }));
        }
    }, [versions, currConversation, dispatch]);

    return (
        <div className={styles.messageContainer}>
            <div className={`${styles.messageContent} ${classRole}`}>
                <p>{message.content}</p>
                <AdditionalInfo
                    isUser={isUser}
                    message={message}
                    isStreaming={isStreaming}
                    versionsProps={{ switchVersion, currVersionId: currVersion?.id }}
                    editProps={{ messageEditConfirm: regenerateUserResponse }}
                />
            </div>
        </div>
    );
};

export default Message;
