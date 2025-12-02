from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Text, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(String(50), default="Analyst", nullable=False)
    status = Column(String(50), default="Inactive", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ResetToken(Base):
    __tablename__ = "reset_tokens"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    token = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)

class Client(Base):
    __tablename__ = "clients"

    id = Column("ID", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(Text, nullable=True)
    other_names = Column(Text, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    profile_photo = Column(Text, nullable=True)
    sex = Column(String, nullable=True)
    organization = Column(Text, nullable=True)
    status = Column(String, default="pending", nullable=True)
    risk_score = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    employer = Column(Text, nullable=True)

    # Assignment fields
    analyst_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    analyst = relationship("User", backref="assigned_clients")

class ClientEmail(Base):
    __tablename__ = "client_emails"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    email = Column(Text, nullable=False)
    status = Column(Text, nullable=True)
    validation_sources = Column(ARRAY(Text), default=list, nullable=True)
    email_tag = Column(Boolean, default=False, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    client = relationship("Client", backref="emails")

class ClientPhoneNumber(Base):
    __tablename__ = "client_phone_numbers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    phone_number = Column(Text, nullable=False)
    client_provided = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    client = relationship("Client", backref="phone_numbers")

class ClientUsername(Base):
    __tablename__ = "client_username"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    username = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    client = relationship("Client", backref="usernames")

class ClientRelativeAssociate(Base):
    __tablename__ = "client_relatives_and_associates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    relationship_type = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    client = relationship("Client", backref="relatives_associates")

class ClientAddress(Base):
    __tablename__ = "client_addresses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    address = Column(Text, nullable=False)
    address_line_1 = Column(Text, nullable=True)
    address_line_2 = Column(Text, nullable=True)
    city = Column(Text, nullable=True)
    state = Column(Text, nullable=True)
    zip = Column(Text, nullable=True)
    client_provided = Column(String, default="No", nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    client = relationship("Client", backref="addresses")

class ClientSocialAccount(Base):
    __tablename__ = "client_social_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    platform = Column(String, nullable=False)
    profile_url = Column(Text, nullable=False)
    what_is_exposed = Column(ARRAY(Text), nullable=True)
    engagement_level = Column(String, nullable=True)
    confidence_level = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    client = relationship("Client", backref="social_accounts")

class ClientResidentialHeatmapImage(Base):
    __tablename__ = "client_residential_and_heatmap_images"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    image_type = Column(String, nullable=False)
    image_url = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    client = relationship("Client", backref="residential_heatmap_images")

class ClientDonorRecord(Base):
    __tablename__ = "client_donor_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    contributor_name = Column(Text, nullable=True)
    recipient = Column(Text, nullable=True)
    recipient_date = Column(Date, nullable=True)
    contribution_amount = Column(Text, nullable=True)
    csv_file = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    client = relationship("Client", backref="donor_records")
    
class ClientVoterRecord(Base):
    __tablename__ = "client_voter_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    voter_record = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    client = relationship("Client", backref="voter_records")

class ClientDVMRecord(Base):
    __tablename__ = "client_dvm_records"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    dvm_record = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="dvm_records")

class ClientGovRecord(Base):
    __tablename__ = "client_government_records"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    record_type = Column(String, nullable=False)
    record = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="gov_records")

class ClientBusinessInfo(Base):
    __tablename__ = "client_business_info"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    business_name = Column(String, nullable=False)
    business_information = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="business_info")

class ClientFacialRecognitionURL(Base):
    __tablename__ = "client_facial_recognition_urls"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    url = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="facial_recognition_urls")

class ClientBrokerScreenRecord(Base):
    __tablename__ = "client_broker_screen_records"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    broker_name = Column(String, nullable=False)
    image_url = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="broker_screen_records")

class ClientFacialRecognitionSite(Base):
    __tablename__ = "client_facial_recognition_sites"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    site_name = Column(String, nullable=False)
    image_url = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="facial_recognition_sites")

class ClientBreachedRecord(Base):
    __tablename__ = "client_breached_records"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    file_url = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="breached_records")

class ClientLeakedDataset(Base):
    __tablename__ = "client_leaked_datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    dataset_name = Column(Text, nullable=False) 
    leak_data = Column(Text, nullable=False)
    email = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="leaked_datasets")

class ClientOsintModuleResult(Base):
    __tablename__ = "client_osint_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    module_name = Column(Text, nullable=False)
    status = Column(Text, nullable=True)
    reliable = Column(Boolean, nullable=False, default=False)
    data = Column(Text, nullable=True)
    front_schema = Column(Text, nullable=True)
    spec_format = Column(Text, nullable=True)
    query = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="osint_module_results")

class ClientSerpAnalysis(Base):
    __tablename__ = "client_serp_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    record_id = Column(Text, nullable=False)
    type = Column(Text, nullable=True)
    title = Column(Text, nullable=True)
    page_rank = Column(Integer, nullable=True)
    domain = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="serp_analysis")

class ClientAIAnalysis(Base):
    __tablename__ = "client_ai_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    model = Column(Text, nullable=False)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="ai_analysis")

class ClientMatchingResult(Base):
    __tablename__ = "client_matching_results"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    matching_result = Column(Text, nullable=False)
    client_data = Column(Text, nullable=False)
    module_data = Column(Text, nullable=False)
    email = Column(Text, nullable=False)
    module = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="matching_results")

# Property Assessment Models
class ClientFrontHouseRecord(Base):
    __tablename__ = "client_front_house_records"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    home_visible_from_street = Column(String, nullable=True)
    exterior_lighting = Column(String, nullable=True)
    surveillance_cameras = Column(String, nullable=True)
    motion_sensors_alarms = Column(String, nullable=True)
    ground_floor_windows_accessible = Column(String, nullable=True)
    bars_locks_reinforced_glass = Column(String, nullable=True)
    gate_fence = Column(String, nullable=True)
    obstruction_of_view = Column(String, nullable=True)
    security_signage = Column(String, nullable=True)
    images = Column(ARRAY(Text), default=list, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="front_house_records")

class ClientBackHouseRecord(Base):
    __tablename__ = "client_back_house_records"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    rear_entry_door = Column(String, nullable=True)
    ground_floor_windows_accessible = Column(String, nullable=True)
    rear_exterior_lighting = Column(String, nullable=True)
    bars_locks_reinforced_glass = Column(String, nullable=True)
    gate_fence = Column(String, nullable=True)
    obstruction_of_view = Column(String, nullable=True)
    surveillance_cameras = Column(String, nullable=True)
    landscaping_concealment = Column(String, nullable=True)
    outbuildings_visible = Column(String, nullable=True)
    pet_door_present = Column(String, nullable=True)
    images = Column(ARRAY(Text), default=list, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="back_house_records")

class ClientInsideHouseRecord(Base):
    __tablename__ = "client_inside_house_records"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    layout_exposure = Column(String, nullable=True)
    images = Column(ARRAY(Text), default=list, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="inside_house_records")

class ClientGoogleStreetViewRecord(Base):
    __tablename__ = "client_google_street_view_records"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    home_visible_from_street = Column(String, nullable=True)
    exterior_lighting = Column(String, nullable=True)
    surveillance_cameras = Column(String, nullable=True)
    motion_sensors_alarms = Column(String, nullable=True)
    ground_floor_windows_accessible = Column(String, nullable=True)
    bars_locks_reinforced_glass = Column(String, nullable=True)
    gate_fence = Column(String, nullable=True)
    obstruction_of_view = Column(String, nullable=True)
    security_signage = Column(String, nullable=True)
    images = Column(ARRAY(Text), default=list, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="google_street_view_records")

class ClientGeneratedDocument(Base):
    __tablename__ = "client_generated_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.ID", ondelete="CASCADE"), nullable=False)
    client_name = Column(Text, nullable=False)
    file_name = Column(Text, nullable=False)
    view_url = Column(Text, nullable=False)          # View in browser
    download_url = Column(Text, nullable=False)      # Direct download
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client = relationship("Client", backref="generated_documents")