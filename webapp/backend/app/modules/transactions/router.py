from fastapi import APIRouter, Depends, Path, HTTPException
from app.core.guards import require_roles
from app.modules.transactions.schemas import TransactionUpdateRequest
from app.modules.transactions.service import transaction_service

router = APIRouter(tags=["transactions"])

@router.get("/transactions/{transaction_id}", dependencies=[Depends(require_roles("auditor", "admin"))])
def get_transaction_detail(transaction_id: str = Path(..., description="Transaction ID to look up")):
    res = transaction_service.get_transaction_detail(transaction_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"Transaction not found: {transaction_id}")
    return res

@router.put("/transactions/{transaction_id}", dependencies=[Depends(require_roles("auditor", "admin"))])
def update_transaction(
    transaction_id: str = Path(..., description="Target transaction ID"),
    req: TransactionUpdateRequest = ...,
):
    update_data = req.dict(exclude_unset=True)
    res = transaction_service.update_transaction(transaction_id, update_data)
    if not res:
        raise HTTPException(status_code=404, detail=f"Transaction not found: {transaction_id}")
    return {
        "status": "success",
        "message": f"Transaction {transaction_id} updated successfully.",
        "data": res
    }
