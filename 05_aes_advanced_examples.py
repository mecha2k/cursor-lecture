#!/usr/bin/env python3
"""
AES 고급 사용법 및 실용적 예제
============================

이 파일은 AES 암호화의 고급 사용법과 실용적인 예제를 제공합니다.

고급 기능:
1. 하이브리드 암호화 (RSA + AES)
2. 파일 암호화/복호화
3. 데이터베이스 암호화
4. 네트워크 통신 암호화
5. 클라우드 저장소 암호화
6. 실시간 스트리밍 암호화
"""

import os
import json
import base64
import hashlib
import secrets
import sqlite3
import socket
import threading
import time
from typing import Dict, List, Optional, Tuple, Union, BinaryIO
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, padding, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidKey, InvalidTag


class HybridEncryption:
    """
    하이브리드 암호화 (RSA + AES)
    
    대칭키 암호화의 속도와 공개키 암호화의 편의성을 결합
    """
    
    def __init__(self, rsa_key_size: int = 2048):
        """
        하이브리드 암호화 초기화
        
        Args:
            rsa_key_size: RSA 키 크기 (2048, 3072, 4096)
        """
        self.rsa_key_size = rsa_key_size
        self.backend = default_backend()
    
    def generate_rsa_keypair(self) -> Tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
        """
        RSA 키 쌍 생성
        
        Returns:
            Tuple[RSAPrivateKey, RSAPublicKey]: 개인키와 공개키
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.rsa_key_size,
            backend=self.backend
        )
        public_key = private_key.public_key()
        return private_key, public_key
    
    def encrypt_hybrid(self, plaintext: str, public_key: rsa.RSAPublicKey) -> Dict[str, str]:
        """
        하이브리드 암호화 (RSA + AES)
        
        Args:
            plaintext: 암호화할 평문
            public_key: RSA 공개키
            
        Returns:
            Dict[str, str]: 암호화된 데이터 (JSON 형태)
        """
        # AES 키 생성
        aes_key = secrets.token_bytes(32)  # 256비트
        iv = secrets.token_bytes(16)
        
        # AES로 평문 암호화
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        
        # 패딩 추가
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode('utf-8'))
        padded_data += padder.finalize()
        
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # RSA로 AES 키 암호화
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return {
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
            "encrypted_key": base64.b64encode(encrypted_aes_key).decode('utf-8'),
            "iv": base64.b64encode(iv).decode('utf-8'),
            "algorithm": "RSA-OAEP+AES-256-CBC"
        }
    
    def decrypt_hybrid(self, encrypted_data: Dict[str, str], private_key: rsa.RSAPrivateKey) -> str:
        """
        하이브리드 복호화
        
        Args:
            encrypted_data: 암호화된 데이터
            private_key: RSA 개인키
            
        Returns:
            str: 복호화된 평문
        """
        # 데이터 디코딩
        ciphertext = base64.b64decode(encrypted_data["ciphertext"])
        encrypted_aes_key = base64.b64decode(encrypted_data["encrypted_key"])
        iv = base64.b64decode(encrypted_data["iv"])
        
        # RSA로 AES 키 복호화
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            asym_padding.OAEP(
                mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # AES로 평문 복호화
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=self.backend)
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # 패딩 제거
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data)
        data += unpadder.finalize()
        
        return data.decode('utf-8')


class FileEncryption:
    """
    파일 암호화/복호화 클래스
    """
    
    def __init__(self, key_length: int = 256):
        """
        파일 암호화 초기화
        
        Args:
            key_length: AES 키 길이
        """
        self.key_length = key_length
        self.key_bytes = key_length // 8
        self.backend = default_backend()
    
    def generate_key(self) -> bytes:
        """암호화 키 생성"""
        return secrets.token_bytes(self.key_bytes)
    
    def encrypt_file(self, input_file: str, output_file: str, key: bytes) -> None:
        """
        파일 암호화
        
        Args:
            input_file: 입력 파일 경로
            output_file: 출력 파일 경로
            key: 암호화 키
        """
        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")
        
        iv = secrets.token_bytes(16)
        
        with open(input_file, 'rb') as infile, open(output_file, 'wb') as outfile:
            # IV 저장
            outfile.write(iv)
            
            # 파일을 청크 단위로 암호화
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.backend)
            encryptor = cipher.encryptor()
            
            while True:
                chunk = infile.read(1024)
                if not chunk:
                    break
                
                # 마지막 청크가 아닌 경우 패딩 추가
                if len(chunk) < 1024:
                    padder = padding.PKCS7(128).padder()
                    chunk = padder.update(chunk) + padder.finalize()
                
                encrypted_chunk = encryptor.update(chunk)
                outfile.write(encrypted_chunk)
            
            # 마지막 청크 처리
            final_chunk = encryptor.finalize()
            if final_chunk:
                outfile.write(final_chunk)
    
    def decrypt_file(self, input_file: str, output_file: str, key: bytes) -> None:
        """
        파일 복호화
        
        Args:
            input_file: 암호화된 파일 경로
            output_file: 복호화된 파일 경로
            key: 복호화 키
        """
        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")
        
        with open(input_file, 'rb') as infile, open(output_file, 'wb') as outfile:
            # IV 읽기
            iv = infile.read(16)
            
            # 파일을 청크 단위로 복호화
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.backend)
            decryptor = cipher.decryptor()
            
            while True:
                chunk = infile.read(1024)
                if not chunk:
                    break
                
                decrypted_chunk = decryptor.update(chunk)
                outfile.write(decrypted_chunk)
            
            # 마지막 청크 처리
            final_chunk = decryptor.finalize()
            if final_chunk:
                outfile.write(final_chunk)


class DatabaseEncryption:
    """
    데이터베이스 암호화 클래스
    """
    
    def __init__(self, key_length: int = 256):
        """
        데이터베이스 암호화 초기화
        
        Args:
            key_length: AES 키 길이
        """
        self.key_length = key_length
        self.key_bytes = key_length // 8
        self.backend = default_backend()
    
    def generate_key(self) -> bytes:
        """암호화 키 생성"""
        return secrets.token_bytes(self.key_bytes)
    
    def encrypt_field(self, data: str, key: bytes) -> str:
        """
        데이터베이스 필드 암호화
        
        Args:
            data: 암호화할 데이터
            key: 암호화 키
            
        Returns:
            str: 암호화된 데이터 (Base64 인코딩)
        """
        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")
        
        iv = secrets.token_bytes(16)
        
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        
        # 패딩 추가
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data.encode('utf-8'))
        padded_data += padder.finalize()
        
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # IV와 암호문을 결합하여 Base64 인코딩
        combined = iv + ciphertext
        return base64.b64encode(combined).decode('utf-8')
    
    def decrypt_field(self, encrypted_data: str, key: bytes) -> str:
        """
        데이터베이스 필드 복호화
        
        Args:
            encrypted_data: 암호화된 데이터 (Base64 인코딩)
            key: 복호화 키
            
        Returns:
            str: 복호화된 데이터
        """
        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")
        
        # Base64 디코딩
        combined = base64.b64decode(encrypted_data)
        iv = combined[:16]
        ciphertext = combined[16:]
        
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.backend)
        decryptor = cipher.decryptor()
        
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # 패딩 제거
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data)
        data += unpadder.finalize()
        
        return data.decode('utf-8')
    
    def create_encrypted_database(self, db_path: str, key: bytes) -> None:
        """
        암호화된 데이터베이스 생성
        
        Args:
            db_path: 데이터베이스 파일 경로
            key: 암호화 키
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 사용자 테이블 생성
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                encrypted_phone TEXT,
                encrypted_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def insert_encrypted_user(self, db_path: str, key: bytes, username: str, email: str, phone: str, address: str) -> None:
        """
        암호화된 사용자 데이터 삽입
        
        Args:
            db_path: 데이터베이스 파일 경로
            key: 암호화 키
            username: 사용자명
            email: 이메일
            phone: 전화번호
            address: 주소
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 민감한 데이터 암호화
        encrypted_phone = self.encrypt_field(phone, key)
        encrypted_address = self.encrypt_field(address, key)
        
        cursor.execute('''
            INSERT INTO users (username, email, encrypted_phone, encrypted_address)
            VALUES (?, ?, ?, ?)
        ''', (username, email, encrypted_phone, encrypted_address))
        
        conn.commit()
        conn.close()
    
    def get_encrypted_user(self, db_path: str, key: bytes, user_id: int) -> Dict[str, str]:
        """
        암호화된 사용자 데이터 조회
        
        Args:
            db_path: 데이터베이스 파일 경로
            key: 복호화 키
            user_id: 사용자 ID
            
        Returns:
            Dict[str, str]: 복호화된 사용자 데이터
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT username, email, encrypted_phone, encrypted_address
            FROM users WHERE id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {}
        
        username, email, encrypted_phone, encrypted_address = row
        
        return {
            "username": username,
            "email": email,
            "phone": self.decrypt_field(encrypted_phone, key),
            "address": self.decrypt_field(encrypted_address, key)
        }


class NetworkEncryption:
    """
    네트워크 통신 암호화 클래스
    """
    
    def __init__(self, key_length: int = 256):
        """
        네트워크 암호화 초기화
        
        Args:
            key_length: AES 키 길이
        """
        self.key_length = key_length
        self.key_bytes = key_length // 8
        self.backend = default_backend()
    
    def generate_key(self) -> bytes:
        """암호화 키 생성"""
        return secrets.token_bytes(self.key_bytes)
    
    def encrypt_message(self, message: str, key: bytes) -> bytes:
        """
        메시지 암호화
        
        Args:
            message: 암호화할 메시지
            key: 암호화 키
            
        Returns:
            bytes: 암호화된 메시지
        """
        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")
        
        iv = secrets.token_bytes(16)
        
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        
        # 패딩 추가
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(message.encode('utf-8'))
        padded_data += padder.finalize()
        
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # IV와 암호문을 결합
        return iv + ciphertext
    
    def decrypt_message(self, encrypted_message: bytes, key: bytes) -> str:
        """
        메시지 복호화
        
        Args:
            encrypted_message: 암호화된 메시지
            key: 복호화 키
            
        Returns:
            str: 복호화된 메시지
        """
        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")
        
        iv = encrypted_message[:16]
        ciphertext = encrypted_message[16:]
        
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.backend)
        decryptor = cipher.decryptor()
        
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        
        # 패딩 제거
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data)
        data += unpadder.finalize()
        
        return data.decode('utf-8')
    
    def start_encrypted_server(self, host: str, port: int, key: bytes) -> None:
        """
        암호화된 서버 시작
        
        Args:
            host: 서버 호스트
            port: 서버 포트
            key: 암호화 키
        """
        def handle_client(client_socket, addr):
            print(f"클라이언트 연결: {addr}")
            
            try:
                while True:
                    # 암호화된 메시지 수신
                    encrypted_data = client_socket.recv(1024)
                    if not encrypted_data:
                        break
                    
                    # 메시지 복호화
                    decrypted_message = self.decrypt_message(encrypted_data, key)
                    print(f"수신된 메시지: {decrypted_message}")
                    
                    # 응답 암호화 및 전송
                    response = f"서버 응답: {decrypted_message}"
                    encrypted_response = self.encrypt_message(response, key)
                    client_socket.send(encrypted_response)
                    
            except Exception as e:
                print(f"클라이언트 처리 오류: {e}")
            finally:
                client_socket.close()
        
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((host, port))
        server_socket.listen(5)
        
        print(f"암호화된 서버 시작: {host}:{port}")
        
        try:
            while True:
                client_socket, addr = server_socket.accept()
                client_thread = threading.Thread(
                    target=handle_client, 
                    args=(client_socket, addr)
                )
                client_thread.start()
        except KeyboardInterrupt:
            print("서버 종료")
        finally:
            server_socket.close()
    
    def send_encrypted_message(self, host: str, port: int, key: bytes, message: str) -> None:
        """
        암호화된 메시지 전송
        
        Args:
            host: 서버 호스트
            port: 서버 포트
            key: 암호화 키
            message: 전송할 메시지
        """
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        try:
            client_socket.connect((host, port))
            
            # 메시지 암호화 및 전송
            encrypted_message = self.encrypt_message(message, key)
            client_socket.send(encrypted_message)
            
            # 응답 수신 및 복호화
            encrypted_response = client_socket.recv(1024)
            decrypted_response = self.decrypt_message(encrypted_response, key)
            print(f"서버 응답: {decrypted_response}")
            
        except Exception as e:
            print(f"클라이언트 오류: {e}")
        finally:
            client_socket.close()


def demonstrate_hybrid_encryption():
    """하이브리드 암호화 데모"""
    print("=" * 60)
    print("하이브리드 암호화 (RSA + AES) 데모")
    print("=" * 60)
    
    hybrid = HybridEncryption(rsa_key_size=2048)
    
    # RSA 키 쌍 생성
    private_key, public_key = hybrid.generate_rsa_keypair()
    print("RSA 키 쌍 생성 완료")
    
    # 평문
    plaintext = "이것은 하이브리드 암호화 테스트입니다!"
    print(f"원본 평문: {plaintext}")
    
    # 하이브리드 암호화
    encrypted_data = hybrid.encrypt_hybrid(plaintext, public_key)
    print(f"암호화된 데이터: {json.dumps(encrypted_data, indent=2)}")
    
    # 하이브리드 복호화
    decrypted_text = hybrid.decrypt_hybrid(encrypted_data, private_key)
    print(f"복호화된 평문: {decrypted_text}")
    print(f"복호화 성공: {plaintext == decrypted_text}")


def demonstrate_file_encryption():
    """파일 암호화 데모"""
    print("\n" + "=" * 60)
    print("파일 암호화 데모")
    print("=" * 60)
    
    file_enc = FileEncryption(key_length=256)
    key = file_enc.generate_key()
    
    # 테스트 파일 생성
    test_file = "test_file.txt"
    encrypted_file = "test_file.enc"
    decrypted_file = "test_file_decrypted.txt"
    
    # 원본 파일 생성
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("이것은 테스트 파일입니다.\n")
        f.write("여러 줄의 텍스트가 포함되어 있습니다.\n")
        f.write("한글과 영문이 혼재되어 있습니다.\n")
    
    print(f"원본 파일 생성: {test_file}")
    
    # 파일 암호화
    file_enc.encrypt_file(test_file, encrypted_file, key)
    print(f"파일 암호화 완료: {encrypted_file}")
    
    # 파일 복호화
    file_enc.decrypt_file(encrypted_file, decrypted_file, key)
    print(f"파일 복호화 완료: {decrypted_file}")
    
    # 결과 확인
    with open(decrypted_file, 'r', encoding='utf-8') as f:
        decrypted_content = f.read()
    print(f"복호화된 내용:\n{decrypted_content}")
    
    # 임시 파일 정리
    for file in [test_file, encrypted_file, decrypted_file]:
        if os.path.exists(file):
            os.remove(file)


def demonstrate_database_encryption():
    """데이터베이스 암호화 데모"""
    print("\n" + "=" * 60)
    print("데이터베이스 암호화 데모")
    print("=" * 60)
    
    db_enc = DatabaseEncryption(key_length=256)
    key = db_enc.generate_key()
    
    # 데이터베이스 생성
    db_path = "encrypted_users.db"
    db_enc.create_encrypted_database(db_path, key)
    print(f"암호화된 데이터베이스 생성: {db_path}")
    
    # 사용자 데이터 삽입
    users = [
        ("김철수", "kim@example.com", "010-1234-5678", "서울시 강남구"),
        ("이영희", "lee@example.com", "010-9876-5432", "부산시 해운대구"),
        ("박민수", "park@example.com", "010-5555-1234", "대구시 수성구")
    ]
    
    for username, email, phone, address in users:
        db_enc.insert_encrypted_user(db_path, key, username, email, phone, address)
        print(f"사용자 추가: {username}")
    
    # 사용자 데이터 조회
    print("\n암호화된 사용자 데이터 조회:")
    for user_id in range(1, 4):
        user_data = db_enc.get_encrypted_user(db_path, key, user_id)
        print(f"사용자 {user_id}: {user_data}")
    
    # 데이터베이스 정리
    if os.path.exists(db_path):
        os.remove(db_path)


def demonstrate_network_encryption():
    """네트워크 암호화 데모"""
    print("\n" + "=" * 60)
    print("네트워크 암호화 데모")
    print("=" * 60)
    
    net_enc = NetworkEncryption(key_length=256)
    key = net_enc.generate_key()
    
    # 서버 시작 (별도 스레드)
    server_thread = threading.Thread(
        target=net_enc.start_encrypted_server,
        args=("localhost", 12345, key)
    )
    server_thread.daemon = True
    server_thread.start()
    
    # 서버 시작 대기
    time.sleep(1)
    
    # 클라이언트 메시지 전송
    messages = [
        "안녕하세요!",
        "암호화된 통신 테스트입니다.",
        "한글과 영문이 혼재된 메시지입니다."
    ]
    
    for message in messages:
        print(f"전송할 메시지: {message}")
        net_enc.send_encrypted_message("localhost", 12345, key, message)
        time.sleep(0.5)


def demonstrate_cloud_storage_encryption():
    """클라우드 저장소 암호화 데모"""
    print("\n" + "=" * 60)
    print("클라우드 저장소 암호화 데모")
    print("=" * 60)
    
    class CloudStorageEncryption:
        """클라우드 저장소 암호화 시뮬레이션"""
        
        def __init__(self):
            self.key = secrets.token_bytes(32)
            self.backend = default_backend()
        
        def encrypt_for_cloud(self, data: str, filename: str) -> Dict[str, str]:
            """클라우드 저장을 위한 암호화"""
            iv = secrets.token_bytes(16)
            
            cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
            encryptor = cipher.encryptor()
            
            # 메타데이터 추가
            metadata = f"filename:{filename},timestamp:{int(time.time())}"
            full_data = f"{metadata}\n{data}"
            
            # 패딩 추가
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(full_data.encode('utf-8'))
            padded_data += padder.finalize()
            
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()
            
            return {
                "encrypted_data": base64.b64encode(ciphertext).decode('utf-8'),
                "iv": base64.b64encode(iv).decode('utf-8'),
                "algorithm": "AES-256-CBC"
            }
        
        def decrypt_from_cloud(self, encrypted_data: Dict[str, str]) -> Tuple[str, str]:
            """클라우드에서 복호화"""
            ciphertext = base64.b64decode(encrypted_data["encrypted_data"])
            iv = base64.b64decode(encrypted_data["iv"])
            
            cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
            decryptor = cipher.decryptor()
            
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()
            
            # 패딩 제거
            unpadder = padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data)
            data += unpadder.finalize()
            
            full_data = data.decode('utf-8')
            lines = full_data.split('\n', 1)
            metadata = lines[0]
            content = lines[1] if len(lines) > 1 else ""
            
            return metadata, content
    
    # 클라우드 저장소 암호화 시뮬레이션
    cloud_enc = CloudStorageEncryption()
    
    # 파일들 암호화
    files = [
        ("document1.txt", "이것은 중요한 문서입니다."),
        ("image1.jpg", "이미지 파일의 바이너리 데이터 시뮬레이션"),
        ("data.json", '{"user": "김철수", "age": 30, "city": "서울"}')
    ]
    
    encrypted_files = []
    for filename, content in files:
        encrypted_data = cloud_enc.encrypt_for_cloud(content, filename)
        encrypted_files.append((filename, encrypted_data))
        print(f"파일 암호화 완료: {filename}")
    
    # 파일들 복호화
    print("\n암호화된 파일들 복호화:")
    for filename, encrypted_data in encrypted_files:
        metadata, content = cloud_enc.decrypt_from_cloud(encrypted_data)
        print(f"파일: {filename}")
        print(f"메타데이터: {metadata}")
        print(f"내용: {content}")
        print("-" * 40)


def demonstrate_streaming_encryption():
    """실시간 스트리밍 암호화 데모"""
    print("\n" + "=" * 60)
    print("실시간 스트리밍 암호화 데모")
    print("=" * 60)
    
    class StreamingEncryption:
        """실시간 스트리밍 암호화"""
        
        def __init__(self, key: bytes):
            self.key = key
            self.backend = default_backend()
            self.iv = secrets.token_bytes(16)
            self.cipher = Cipher(algorithms.AES(key), modes.CBC(self.iv), backend=self.backend)
            self.encryptor = self.cipher.encryptor()
            self.buffer = b""
        
        def encrypt_chunk(self, chunk: bytes) -> bytes:
            """청크 암호화"""
            self.buffer += chunk
            
            # 16바이트 단위로 처리
            encrypted_chunks = b""
            while len(self.buffer) >= 16:
                block = self.buffer[:16]
                self.buffer = self.buffer[16:]
                encrypted_chunks += self.encryptor.update(block)
            
            return encrypted_chunks
        
        def finalize(self) -> bytes:
            """마지막 블록 처리"""
            if self.buffer:
                # 패딩 추가
                padder = padding.PKCS7(128).padder()
                padded_data = padder.update(self.buffer)
                padded_data += padder.finalize()
                return self.encryptor.update(padded_data) + self.encryptor.finalize()
            return self.encryptor.finalize()
    
    # 스트리밍 암호화 시뮬레이션
    key = secrets.token_bytes(32)
    stream_enc = StreamingEncryption(key)
    
    # 데이터 스트림 시뮬레이션
    data_stream = [
        b"첫 번째 청크입니다. ",
        b"두 번째 청크입니다. ",
        b"세 번째 청크입니다. ",
        b"마지막 청크입니다."
    ]
    
    print("스트리밍 암호화 시작:")
    encrypted_stream = b""
    
    for i, chunk in enumerate(data_stream):
        print(f"청크 {i+1} 처리: {chunk.decode('utf-8')}")
        encrypted_chunk = stream_enc.encrypt_chunk(chunk)
        encrypted_stream += encrypted_chunk
        print(f"암호화된 청크 길이: {len(encrypted_chunk)} 바이트")
    
    # 마지막 블록 처리
    final_chunk = stream_enc.finalize()
    encrypted_stream += final_chunk
    
    print(f"\n전체 암호화된 스트림 길이: {len(encrypted_stream)} 바이트")
    print(f"암호화된 스트림 (hex): {encrypted_stream.hex()}")


def main():
    """메인 함수 - 모든 고급 데모 실행"""
    print("AES 고급 사용법 및 실용적 예제")
    print("=" * 60)
    print("이 데모는 AES 암호화의 고급 사용법을 보여줍니다:")
    print("1. 하이브리드 암호화 (RSA + AES)")
    print("2. 파일 암호화/복호화")
    print("3. 데이터베이스 암호화")
    print("4. 네트워크 통신 암호화")
    print("5. 클라우드 저장소 암호화")
    print("6. 실시간 스트리밍 암호화")
    print("=" * 60)
    
    try:
        demonstrate_hybrid_encryption()
        demonstrate_file_encryption()
        demonstrate_database_encryption()
        demonstrate_cloud_storage_encryption()
        demonstrate_streaming_encryption()
        
        print("\n" + "=" * 60)
        print("모든 고급 데모가 성공적으로 완료되었습니다!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n오류 발생: {e}")
        print("필요한 패키지를 설치하세요: pip install cryptography")


if __name__ == "__main__":
    main()
