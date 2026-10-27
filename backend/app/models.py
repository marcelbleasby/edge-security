from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class SecurityEvent(Base):
    __tablename__ = 'security_events'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    sensor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    src_ip: Mapped[str | None] = mapped_column(String(45))
    dest_ip: Mapped[str | None] = mapped_column(String(45))
    src_port: Mapped[int | None] = mapped_column(Integer)
    dest_port: Mapped[int | None] = mapped_column(Integer)
    proto: Mapped[str | None] = mapped_column(String(24))
    signature_id: Mapped[int | None] = mapped_column(BigInteger)
    severity: Mapped[int | None] = mapped_column(Integer)
    signature: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(String(253))
    raw: Mapped[dict] = mapped_column(JSON, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index('ix_event_sensor_time', 'sensor_id', 'timestamp'), Index('ix_event_type_time', 'event_type', 'timestamp'), Index('ix_event_src_time', 'src_ip', 'timestamp'))

class CollectorCheckpoint(Base):
    __tablename__ = 'collector_checkpoints'
    sensor_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    file_identity: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_offset: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class NetworkDevice(Base):
    __tablename__ = 'network_devices'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sensor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)
    name: Mapped[str | None] = mapped_column(String(150))
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint('sensor_id', 'ip', name='uq_device_sensor_ip'),)

class DomainPolicy(Base):
    __tablename__ = 'domain_policies'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)  # allow | watch | deny
    include_subdomains: Mapped[bool] = mapped_column(nullable=False, default=True)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    description: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint('domain', name='uq_domain_policy_domain'),)

class DNSDeployment(Base):
    __tablename__ = 'dns_deployments'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    policy_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('domain_policies.id', ondelete='SET NULL'))
    domain: Mapped[str] = mapped_column(String(253), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default='deployed')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    __table_args__ = (UniqueConstraint('domain', 'action', name='uq_dns_deployment_domain_action'),)

class DNSAuditLog(Base):
    __tablename__ = 'dns_audit_logs'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(String(32), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(253))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class DNSPolicyGroups(Base):
    __tablename__ = 'dns_policy_groups'
    policy_id: Mapped[int] = mapped_column(BigInteger, ForeignKey('domain_policies.id', ondelete='CASCADE'), primary_key=True)
    group_ids: Mapped[list] = mapped_column(JSON, nullable=False)


class AdminSession(Base):
    __tablename__ = 'admin_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class DNSChange(Base):
    __tablename__ = 'dns_changes'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    deployment_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    before_state: Mapped[dict] = mapped_column(JSON, nullable=False)
    after_state: Mapped[dict] = mapped_column(JSON, nullable=False)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reverted_by: Mapped[int | None] = mapped_column(BigInteger)
