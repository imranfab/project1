import React from 'react';
import styles from "../../styles/chat/Message.module.css";
import Message from "./Message";

const Conversation = ({ messages = [], regenerateUserResponse, error }) => {
    if (!Array.isArray(messages)) return null;

    return (
        <>
            {messages.filter(Boolean).map(m => (
                <Message
                    key={m.id}
                    message={m}
                    regenerateUserResponse={regenerateUserResponse}
                />
            ))}
            {error && (
                <div className={styles.messageContent}>
                    <p className={styles.error}>{error}</p>
                </div>
            )}
        </>
    );
};

export default Conversation;
