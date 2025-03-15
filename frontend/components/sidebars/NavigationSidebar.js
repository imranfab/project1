import React, { useCallback } from "react";
import Link from "next/link";
import Sidebar from "./Sidebar";
import styles from '../../styles/sidebars/Sidebar.module.css';
import { useDispatch, useSelector } from "react-redux";
import { postLogoutThunk } from "../../redux/auth";

const NavigationSidebar = () => {
    const auth = useSelector(state => state.auth);
    const csrfToken = auth.csrfToken;
    const user = auth.user; 
    const dispatch = useDispatch();

    console.log(auth)

    const renderLogout = () => {
        if (csrfToken === null) {
            return null;
        }

        return (
            <>
               
                <Link
                    className={styles.logoutContainer}
                    href={"/"}
                    onClick={() => {
                        dispatch(postLogoutThunk({ csrfToken }));
                    }}
                >
                    <span>Logout</span>
                </Link>
            </>
        );
    };

    const navElements = useCallback(() => {
        return (
            <> {/* Display Logged-in User */}
            {user && (
                <div className={styles.userContainer}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="white" viewBox="0 0 24 24">
                        <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm0 3a3 3 0 110 6 3 3 0 010-6zm0 14.2c-2.5 0-4.7-1.1-6.2-2.8.1-2 4.1-3.2 6.2-3.2s6.1 1.2 6.2 3.2c-1.5 1.7-3.7 2.8-6.2 2.8z"/>
                    </svg>
                    <span className={styles.userName}>{user}</span>
                </div>
            )}

            {/* Logout Button */}
                <Link href={"/"}>
                    <h1>Internal<br />ChatGPT</h1>
                </Link>
                <ul>
                    <Link href="/">
                        <li>Chat</li>
                    </Link>
                    <Link href="/">
                        <li>Knowledge Bases</li>
                    </Link>
                    <Link href="/">
                        <li>Work with file</li>
                    </Link>
                    <Link href="/">
                        <li>Work with 2 files</li>
                    </Link>
                </ul>
                {renderLogout()}
            </>
        );
    }, [auth]);

    const description = "Chat Types";
    return (
        <Sidebar navElements={navElements} description={description} />
    );
}

export default NavigationSidebar;
