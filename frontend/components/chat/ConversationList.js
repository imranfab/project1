import { useEffect, useState } from "react";
import { fetchConversationSummaries } from "../../utils/chatApi";

export default function ConversationList() {
  const [conversations, setConversations] = useState([]);

  useEffect(() => {
    fetchConversationSummaries(1, 5, "")
      .then(data => setConversations(data.results));
  }, []);

  return (
    <div>
      <h3>Previous Conversations</h3>
      {conversations.map(c => (
        <div key={c.id}>{c.title}</div>
      ))}
    </div>
  );
}
