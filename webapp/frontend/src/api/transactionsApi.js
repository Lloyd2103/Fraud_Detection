import client from './client';

export const transactionsApi = {
  fetchTransactionDetail: (id) => client.get(`/transactions/${id}`),
  updateTransaction: (transactionId, payload) =>
    client.put(`/transactions/${transactionId}`, payload),
};

export default transactionsApi;

