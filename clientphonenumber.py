@router.post("/clients/{client_id}/phone-numbers/bulk-upload", tags=["Client Phone Numbers"])
def bulk_upload_phone_numbers(
    client_id: uuid.UUID,
    bulk_data: BulkPhoneUpload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send raw phone numbers directly to webhook and return real n8n result"""
    
    # Check client access
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if current_user.role == "Analyst" and client.analyst_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Clean and normalize phone numbers
    phone_lines = bulk_data.phone_numbers_text.strip().split('\n')
    normalized_phones = []
    for line in phone_lines:
        phone = line.strip()
        if phone:
            cleaned_phone = clean_phone_number(phone)
            normalized_phones.append(cleaned_phone)
    
    normalized_text = '\n'.join(normalized_phones)
    
    webhook_url = "https://obscureiq.app.n8n.cloud/webhook/92457ed2-aad5-4981-b88c-cd65f11b3a8b"
    
    payload = {
        "phone_number": normalized_text,
        "client_id": str(client_id),
        "client_provided": bulk_data.client_provided
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=60)

        try:
            n8n_result = response.json()
        except ValueError:
            raise HTTPException(
                status_code=500,
                detail="Webhook did not return valid JSON"
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=n8n_result.get("message", "Webhook failed")
            )

        success = n8n_result.get("success")

        if success is True:
            return {
                "status": "success",
                "message": n8n_result.get("message", "Phone numbers added successfully")
            }

        if success is False:
            raise HTTPException(
                status_code=400,
                detail=n8n_result.get("message", "Phone number already exists")
            )

        raise HTTPException(
            status_code=500,
            detail="Unexpected webhook response"
        )

    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Webhook connection error: {str(e)}"
        )
