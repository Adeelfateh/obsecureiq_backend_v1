from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
from datetime import datetime, date
import uuid

# User Schemas
class UserSignup(BaseModel):
    full_name: str
    email: str
    password: str
    confirm_password: str

class UserLogin(BaseModel):
    email: str
    password: str

class PasswordResetRequest(BaseModel):
    email: str

class PasswordReset(BaseModel):
    token: str
    new_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserUpdate(BaseModel):
    full_name: str
    email: str
    role: str
    status: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    status: str
    created_at: datetime

class AdminAddUser(BaseModel):
    full_name: str
    email: str
    role: str
    status: str

class ChangePassword(BaseModel):
    old_password: str
    new_password: str

# Client Schemas
class ClientResponse(BaseModel):
    id: uuid.UUID = Field(..., alias="ID")
    full_name: str | None = None
    other_names: str | None = None
    date_of_birth: datetime | None = None
    profile_photo: str | None = None
    sex: str | None = None
    organization: str | None = None
    status: str | None = None
    risk_score: str | None = None
    created_at: datetime
    updated_at: datetime
    email: str | None = None
    phone_number: str | None = None
    employer: str | None = None
    darkside_module: bool = False
    snubase_module: bool = False
    analyst_id: int | None = None
    assigned_at: datetime | None = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )

class AssignClientRequest(BaseModel):
    analyst_email: EmailStr

class ClientCreate(BaseModel):
    full_name: str
    other_names: Optional[str] = None
    date_of_birth: Optional[date] = None
    sex: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    employer: Optional[str] = None

# Email Schemas
class EmailCreate(BaseModel):
    email: EmailStr
    status: Optional[str] = None
    validation_sources: Optional[List[str]] = None
    email_tag: Optional[bool] = False

class EmailUpdate(BaseModel):
    email: Optional[EmailStr] = None
    status: Optional[str] = None
    validation_sources: Optional[List[str]] = None
    email_tag: Optional[bool] = None

class EmailResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    email: str
    status: str | None
    validation_sources: List[str] | None
    email_tag: bool | None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class BulkEmailUpload(BaseModel):
    emails_text: str

# Phone Number Schemas
class PhoneNumberCreate(BaseModel):
    phone_number: str
    client_provided: Optional[str] = None

class PhoneNumberUpdate(BaseModel):
    phone_number: Optional[str] = None
    client_provided: Optional[str] = None

class PhoneNumberResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    phone_number: str
    client_provided: str | None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class BulkPhoneUpload(BaseModel):
    phone_numbers_text: str

# Relative/Associate Schemas
class RelativeAssociateCreate(BaseModel):
    name: str
    relationship_type: Optional[str] = None

class RelativeAssociateUpdate(BaseModel):
    name: Optional[str] = None
    relationship_type: Optional[str] = None

class RelativeAssociateResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    name: str
    relationship_type: str | None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class BulkRelativeUpload(BaseModel):
    relatives_text: str
    relationship_type: Optional[str] = "Associate"

# Username Schemas
class UsernameCreate(BaseModel):
    username: str

class UsernameUpdate(BaseModel):
    username: Optional[str] = None
    
class BulkUsernameUpload(BaseModel):
    usernames_text: str

class UsernameResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    username: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Address Schemas
class AddressCreate(BaseModel):
    address: str
    client_provided: Optional[str] = None

class AddressUpdate(BaseModel):
    address: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    client_provided: Optional[str] = None

class AddressResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    address: str
    address_line_1: str | None
    address_line_2: str | None
    city: str | None
    state: str | None
    zip: str | None
    client_provided: str | None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class BulkAddressUpload(BaseModel):
    addresses_text: str

# Social Account Schemas
class SocialAccountCreate(BaseModel):
    platform: str
    profile_url: str
    what_is_exposed: Optional[List[str]] = None
    engagement_level: Optional[str] = None
    confidence_level: Optional[str] = None

class SocialAccountUpdate(BaseModel):
    platform: Optional[str] = None
    profile_url: Optional[str] = None
    what_is_exposed: Optional[List[str]] = None
    engagement_level: Optional[str] = None
    confidence_level: Optional[str] = None

class SocialAccountResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    platform: str
    profile_url: str
    what_is_exposed: List[str] | None
    engagement_level: str | None
    confidence_level: str | None
    image_url: str | None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Residential Heatmap Image Schemas
class ResidentialHeatmapImageResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    image_type: str
    image_url: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Donor Record Schemas
class DonorRecordCreate(BaseModel):
    contributor_name: str
    recipient: str
    recipient_date: Optional[date] = None
    contribution_amount: Optional[str] = None

class DonorRecordUpdate(BaseModel):
    contributor_name: Optional[str] = None
    recipient: Optional[str] = None
    recipient_date: Optional[date] = None
    contribution_amount: Optional[str] = None

class DonorRecordResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    contributor_name: str | None
    recipient: str | None
    recipient_date: date | None
    contribution_amount: str | None
    csv_file: str | None
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Voter Record Schemas
class VoterRecordCreate(BaseModel):
    voter_record: str

class VoterRecordUpdate(BaseModel):
    voter_record: Optional[str] = None

class VoterRecordResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    voter_record: str
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# DVM Record Schemas
class DVMRecordCreate(BaseModel):
    dvm_record: str

class DVMRecordUpdate(BaseModel):
    dvm_record: Optional[str] = None

class DVMRecordResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    dvm_record: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Government Record Schemas
class GovRecordCreate(BaseModel):
    record_type: str
    record: str

class GovRecordUpdate(BaseModel):
    record_type: Optional[str] = None
    record: Optional[str] = None

class GovRecordResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    record_type: str
    record: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Business Info Schemas
class BusinessInfoCreate(BaseModel):
    business_name: str
    business_information: str

class BusinessInfoUpdate(BaseModel):
    business_name: Optional[str] = None
    business_information: Optional[str] = None

class BusinessInfoResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    business_name: str
    business_information: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Facial Recognition Schemas
class FacialRecognitionCreate(BaseModel):
    url: str

class FacialRecognitionUpdate(BaseModel):
    url: str

class FacialRecognitionResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    url: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class FacialRecognitionBulkUpload(BaseModel):
    urls_text: str

# Broker Screen Record Schemas
class BrokerScreenRecordResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    broker_name: str
    image_url: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class BrokerScreenRecordUpdate(BaseModel):
    broker_name: Optional[str] = None

# Facial Recognition Site Schemas
class FacialRecognitionSiteResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    site_name: str
    image_url: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



# SERP Analysis Schemas
class SerpAnalysisResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    type: str | None
    page_rank: int | None
    domain: str | None

    model_config = ConfigDict(from_attributes=True)

# AI Analysis Schemas
class AIAnalysisResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    model: str
    query: str
    answer: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Leaked Dataset Schemas
class LeakedDatasetResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    dataset_name: str
    email: str
    leak_data: str
    module: str | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# OSINT Module Result Schemas
class OsintModuleResultResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    module_name: str
    status: str | None
    reliable: bool
    data: str | None
    front_schema: str | None
    spec_format: str | None
    query: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Client Matching Result Schemas
class ClientMatchingResultResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    matching_result: str
    client_data: str
    module_data: str
    email: str
    module: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Property Assessment Schemas
class FrontHouseRecordCreate(BaseModel):
    home_visible_from_street: Optional[str] = None
    exterior_lighting: Optional[str] = None
    surveillance_cameras: Optional[str] = None
    motion_sensors_alarms: Optional[str] = None
    ground_floor_windows_accessible: Optional[str] = None
    bars_locks_reinforced_glass: Optional[str] = None
    gate_fence: Optional[str] = None
    obstruction_of_view: Optional[str] = None
    security_signage: Optional[str] = None
    images: Optional[List[str]] = None

class FrontHouseRecordUpdate(BaseModel):
    home_visible_from_street: Optional[str] = None
    exterior_lighting: Optional[str] = None
    surveillance_cameras: Optional[str] = None
    motion_sensors_alarms: Optional[str] = None
    ground_floor_windows_accessible: Optional[str] = None
    bars_locks_reinforced_glass: Optional[str] = None
    gate_fence: Optional[str] = None
    obstruction_of_view: Optional[str] = None
    security_signage: Optional[str] = None
    images: Optional[List[str]] = None

class FrontHouseRecordResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    home_visible_from_street: str | None
    exterior_lighting: str | None
    surveillance_cameras: str | None
    motion_sensors_alarms: str | None
    ground_floor_windows_accessible: str | None
    bars_locks_reinforced_glass: str | None
    gate_fence: str | None
    obstruction_of_view: str | None
    security_signage: str | None
    images: List[str] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class BackHouseRecordCreate(BaseModel):
    rear_entry_door: Optional[str] = None
    ground_floor_windows_accessible: Optional[str] = None
    rear_exterior_lighting: Optional[str] = None
    bars_locks_reinforced_glass: Optional[str] = None
    gate_fence: Optional[str] = None
    obstruction_of_view: Optional[str] = None
    surveillance_cameras: Optional[str] = None
    landscaping_concealment: Optional[str] = None
    outbuildings_visible: Optional[str] = None
    pet_door_present: Optional[str] = None
    images: Optional[List[str]] = None

class BackHouseRecordUpdate(BaseModel):
    rear_entry_door: Optional[str] = None
    ground_floor_windows_accessible: Optional[str] = None
    rear_exterior_lighting: Optional[str] = None
    bars_locks_reinforced_glass: Optional[str] = None
    gate_fence: Optional[str] = None
    obstruction_of_view: Optional[str] = None
    surveillance_cameras: Optional[str] = None
    landscaping_concealment: Optional[str] = None
    outbuildings_visible: Optional[str] = None
    pet_door_present: Optional[str] = None
    images: Optional[List[str]] = None

class BackHouseRecordResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    rear_entry_door: str | None
    ground_floor_windows_accessible: str | None
    rear_exterior_lighting: str | None
    bars_locks_reinforced_glass: str | None
    gate_fence: str | None
    obstruction_of_view: str | None
    surveillance_cameras: str | None
    landscaping_concealment: str | None
    outbuildings_visible: str | None
    pet_door_present: str | None
    images: List[str] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InsideHouseRecordCreate(BaseModel):
    layout_exposure: Optional[str] = None
    images: Optional[List[str]] = None

class InsideHouseRecordUpdate(BaseModel):
    layout_exposure: Optional[str] = None
    images: Optional[List[str]] = None

class InsideHouseRecordResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    layout_exposure: str | None
    images: List[str] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class GoogleStreetViewRecordCreate(BaseModel):
    home_visible_from_street: Optional[str] = None
    exterior_lighting: Optional[str] = None
    surveillance_cameras: Optional[str] = None
    motion_sensors_alarms: Optional[str] = None
    ground_floor_windows_accessible: Optional[str] = None
    bars_locks_reinforced_glass: Optional[str] = None
    gate_fence: Optional[str] = None
    obstruction_of_view: Optional[str] = None
    security_signage: Optional[str] = None
    images: Optional[List[str]] = None

class GoogleStreetViewRecordUpdate(BaseModel):
    home_visible_from_street: Optional[str] = None
    exterior_lighting: Optional[str] = None
    surveillance_cameras: Optional[str] = None
    motion_sensors_alarms: Optional[str] = None
    ground_floor_windows_accessible: Optional[str] = None
    bars_locks_reinforced_glass: Optional[str] = None
    gate_fence: Optional[str] = None
    obstruction_of_view: Optional[str] = None
    security_signage: Optional[str] = None
    images: Optional[List[str]] = None

class GoogleStreetViewRecordResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    home_visible_from_street: str | None
    exterior_lighting: str | None
    surveillance_cameras: str | None
    motion_sensors_alarms: str | None
    ground_floor_windows_accessible: str | None
    bars_locks_reinforced_glass: str | None
    gate_fence: str | None
    obstruction_of_view: str | None
    security_signage: str | None
    images: List[str] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
