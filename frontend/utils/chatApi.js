import { axiosInstance } from "../api/axios";


export async function fetchConversationSummaries(
  page = 1,
  pageSize = 5,
  search = ""
) {
  const response = await axiosInstance.get(
    "/chat/conversations/summaries/",
    {
      params: {
        page,
        page_size: pageSize,
        search,
      },
    }
  );

  return response.data;
}
