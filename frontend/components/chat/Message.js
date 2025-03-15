import React, {useCallback, useEffect, useState} from 'react';
import styles from "../../styles/chat/Message.module.css";
import {Prism as SyntaxHighlighter} from 'react-syntax-highlighter';
import {darcula} from "react-syntax-highlighter/dist/cjs/styles/prism";
import {useDispatch, useSelector} from "react-redux";
import {switchConversationVersionThunk} from "../../redux/conversations";
import {setConversation} from "../../redux/currentConversation";
import {AdditionalInfo} from "./MessageAdditionalInfo";


const parseInlineCode = (text) => {
    if (typeof text !== "string") return JSON.stringify(text, null, 2); // Ensure text is a string
    return text.split("`").map((part, index) => index % 2 === 1 ? <code key={index}>{part}</code> : part);
};


const Message = ({message, regenerateUserResponse}) => {
    const isUser = message.role === 'user';
    const classRole = isUser ? styles.user : styles.assistant;
    const versions = message.versions;

    const dispatch = useDispatch();
    const currVersion = useSelector(state => state.currentConversation);
    const currConversation = useSelector(state => state.allConversations.find(c => c.id === currVersion.conversation_id));
    const isStreaming = useSelector(state => state.streaming);

    const [editing, setEditing] = useState(false);
    const [editedMessage, setEditedMessage] = useState('');
    const [numRows, setNumRows] = useState(1);
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        setNumRows(editedMessage.split('\n').length);
    }, [editedMessage]);

    let parts;
        try {
            // Ensure message.content is always treated as a string
            const content = typeof message.content === 'string' ? message.content : JSON.stringify(message.content, null, 2);
            parts = isUser ? [content] : content.split('```');
        } catch (e) {
            console.error("Error processing message.content:", e);
            return null;
        }


    const switchVersion = useCallback((currVersionIndex, where) => {
        let newVersionId;
        if (where === 'left') {
            newVersionId = versions[currVersionIndex - 1].id;
            console.log("left", newVersionId, currConversation.id);
        } else {
            newVersionId = versions[currVersionIndex + 1].id;
            console.log("right", newVersionId, currConversation.id);
        }

        dispatch(switchConversationVersionThunk({conversationId: currConversation.id, versionId: newVersionId}));
        let newVersion = currConversation.versions.find(version => version.id === newVersionId);
        newVersion = {...newVersion, title: currConversation.title};
        console.log("newVersion", newVersion);
        dispatch(setConversation(newVersion));

    }, [versions]);

    const handleCopy = () => {
        const contentToCopy = typeof message.content === "string"
            ? message.content
            : JSON.stringify(message.content, null, 2); 
    
        navigator.clipboard.writeText(contentToCopy)
            .then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 1500);
            })
            .catch(err => console.error("Copy failed", err));
    };
    
    const handleDownload = (code) => {
        // Ensure the code starts with triple backticks and remove the first line
        const codeLines = code.split('\n');
        if (codeLines[0].startsWith('```')) {
            codeLines.shift(); // Remove the first line containing ```language
        }
        const cleanCode = codeLines.join('\n'); // Join the remaining code
    
        // Create a downloadable text file
        const blob = new Blob([cleanCode], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `code-snippet.txt`; // Save as .txt file
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };
    

    const renderAdditionalInfo = () => {
        const editProps = {
            editing,
            setEditing,
            editedMessage,
            setEditedMessage,
            messageEditConfirm: regenerateUserResponse,
        };

        const versionProps = {
            switchVersion,
            currVersionId: currVersion.id,
        };

        return <AdditionalInfo isUser={isUser} message={message} isStreaming={isStreaming} editProps={editProps} versionsProps={versionProps}/>;
    };


    return (
        <div className={`${styles.messageContainer} `}>
            <div className={`${styles.messageContent}  ${classRole}`}>
            
                {editing ? (
                    <textarea
                        value={editedMessage}
                        onChange={(e) => setEditedMessage(e.target.value)}
                        rows={numRows}
                    />
                ) : (
                    parts.map((part, index) => {
                        if (index % 2 === 0) {
                            return typeof part === "string" 
                                ? part.split('\n').map((line, lineIndex) => (
                                    <p key={lineIndex}>{isUser ? line : parseInlineCode(line)}</p>
                                ))
                                : <pre key={index}>{JSON.stringify(part, null, 2)}</pre>;  // Render objects as JSON
                        } else {
                            let [language, ...codeLines] = part.split('\n');
                            let code = codeLines.join('\n');
                            
                            return (
                                <div key={index} className={styles.codeBlockContainer}>
                                    <SyntaxHighlighter language={language} style={darcula}>
                                        {code}
                                    </SyntaxHighlighter>
                                    <button 
                                        className={styles.downloadButton} 
                                        onClick={() => handleDownload(code, language)}
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="yellow"><path d="M480-320 280-520l56-58 104 104v-326h80v326l104-104 56 58-200 200ZM240-160q-33 0-56.5-23.5T160-240v-120h80v120h480v-120h80v120q0 33-23.5 56.5T720-160H240Z"/></svg>
                                    </button>
                                </div>
                            );
                        }
                    })
                )}
                {renderAdditionalInfo()}
                <button className={styles.copyButton} onClick={handleCopy}>
                {copied ? <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="white"><path d="M382-240 154-468l57-57 171 171 367-367 57 57-424 424Z"/></svg>  : <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 -960 960 960" width="24px" fill="white"><path d="M360-240q-33 0-56.5-23.5T280-320v-480q0-33 23.5-56.5T360-880h360q33 0 56.5 23.5T800-800v480q0 33-23.5 56.5T720-240H360Zm0-80h360v-480H360v480ZM200-80q-33 0-56.5-23.5T120-160v-560h80v560h440v80H200Zm160-240v-480 480Z"/></svg>}
            </button>
            
            </div>
            
        </div>
            

    );
};

export default Message;
