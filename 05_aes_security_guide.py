#!/usr/bin/env python3
"""
AES 암호화 보안 모범 사례 가이드
================================

이 파일은 AES 암호화를 사용할 때 지켜야 할 보안 모범 사례와
주의사항을 상세히 설명합니다.

보안 원칙:
1. 키 관리의 중요성
2. 안전한 랜덤 생성
3. 적절한 운영 모드 선택
4. 인증과 무결성 보장
5. 부채널 공격 방어
"""

import os
import secrets
import hashlib
import hmac
from typing import Tuple, Optional, List
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidKey, InvalidTag


class SecureAESManager:
    """
    보안을 고려한 AES 암호화 관리자

    이 클래스는 보안 모범 사례를 적용하여
    안전한 AES 암호화를 제공합니다.
    """

    def __init__(self, key_length: int = 256):
        """
        보안 AES 관리자 초기화

        Args:
            key_length: 키 길이 (128, 192, 256)
        """
        if key_length not in [128, 192, 256]:
            raise ValueError("키 길이는 128, 192, 256 중 하나여야 합니다")

        self.key_length = key_length
        self.key_bytes = key_length // 8
        self.backend = default_backend()

        # 보안 설정
        self.min_password_length = 12
        self.pbkdf2_iterations = 100000  # 보안을 위한 높은 반복 횟수
        self.max_plaintext_length = 1024 * 1024  # 1MB 제한

    def generate_secure_key(self) -> bytes:
        """
        암호학적으로 안전한 키 생성

        Returns:
            bytes: 생성된 키
        """
        return secrets.token_bytes(self.key_bytes)

    def generate_secure_iv(self, mode: str = "GCM") -> bytes:
        """
        안전한 초기화 벡터 생성

        Args:
            mode: 암호화 모드 ("GCM", "CBC", "CTR")

        Returns:
            bytes: 생성된 IV
        """
        if mode == "GCM":
            return secrets.token_bytes(12)  # GCM 권장 길이
        elif mode in ["CBC", "CTR"]:
            return secrets.token_bytes(16)  # AES 블록 크기
        else:
            raise ValueError(f"지원하지 않는 모드: {mode}")

    def validate_password(self, password: str) -> bool:
        """
        비밀번호 강도 검증

        Args:
            password: 검증할 비밀번호

        Returns:
            bool: 비밀번호가 안전한지 여부
        """
        if len(password) < self.min_password_length:
            return False

        # 복잡성 검사
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        return has_upper and has_lower and has_digit and has_special

    def derive_key_securely(
        self,
        password: str,
        salt: Optional[bytes] = None,
        iterations: Optional[int] = None,
    ) -> Tuple[bytes, bytes]:
        """
        안전한 키 유도 (PBKDF2)

        Args:
            password: 사용자 비밀번호
            salt: 솔트 (None이면 자동 생성)
            iterations: 반복 횟수 (None이면 기본값 사용)

        Returns:
            Tuple[bytes, bytes]: (유도된 키, 사용된 솔트)
        """
        if not self.validate_password(password):
            raise ValueError(
                f"비밀번호는 최소 {self.min_password_length}자 이상이고 "
                "대소문자, 숫자, 특수문자를 포함해야 합니다"
            )

        if salt is None:
            salt = secrets.token_bytes(32)  # 256비트 솔트

        if iterations is None:
            iterations = self.pbkdf2_iterations

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.key_bytes,
            salt=salt,
            iterations=iterations,
            backend=self.backend,
        )

        key = kdf.derive(password.encode("utf-8"))
        return key, salt

    def encrypt_with_authentication(
        self, plaintext: str, key: bytes, additional_data: Optional[str] = None
    ) -> Tuple[bytes, bytes, bytes]:
        """
        인증이 포함된 암호화 (GCM 모드)

        Args:
            plaintext: 암호화할 평문
            key: 암호화 키
            additional_data: 추가 인증 데이터

        Returns:
            Tuple[bytes, bytes, bytes]: (암호문, IV, 인증 태그)
        """
        if len(plaintext) > self.max_plaintext_length:
            raise ValueError("평문이 너무 깁니다")

        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")

        iv = self.generate_secure_iv("GCM")

        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=self.backend)
        encryptor = cipher.encryptor()

        # AAD 추가
        if additional_data:
            encryptor.authenticate_additional_data(additional_data.encode("utf-8"))

        ciphertext = encryptor.update(plaintext.encode("utf-8")) + encryptor.finalize()

        return ciphertext, iv, encryptor.tag

    def decrypt_with_authentication(
        self,
        ciphertext: bytes,
        key: bytes,
        iv: bytes,
        tag: bytes,
        additional_data: Optional[str] = None,
    ) -> str:
        """
        인증이 포함된 복호화 (GCM 모드)

        Args:
            ciphertext: 암호문
            key: 복호화 키
            iv: 초기화 벡터
            tag: 인증 태그
            additional_data: 추가 인증 데이터

        Returns:
            str: 복호화된 평문
        """
        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")

        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=self.backend)
        decryptor = cipher.decryptor()

        # AAD 추가
        if additional_data:
            decryptor.authenticate_additional_data(additional_data.encode("utf-8"))

        try:
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            return plaintext.decode("utf-8")
        except InvalidTag:
            raise InvalidTag("인증 실패 - 데이터가 변조되었습니다")

    def encrypt_large_data(
        self, data: bytes, key: bytes, chunk_size: int = 1024
    ) -> List[Tuple[bytes, bytes, bytes]]:
        """
        대용량 데이터를 청크 단위로 암호화

        Args:
            data: 암호화할 데이터
            key: 암호화 키
            chunk_size: 청크 크기

        Returns:
            List[Tuple[bytes, bytes, bytes]]: (암호문, IV, 태그) 리스트
        """
        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")

        encrypted_chunks = []

        for i in range(0, len(data), chunk_size):
            chunk = data[i : i + chunk_size]

            # 각 청크에 고유한 IV 생성
            iv = self.generate_secure_iv("GCM")

            cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=self.backend)
            encryptor = cipher.encryptor()

            # 청크 번호를 AAD로 사용
            chunk_info = f"chunk:{i//chunk_size}:total:{len(data)}"
            encryptor.authenticate_additional_data(chunk_info.encode("utf-8"))

            ciphertext = encryptor.update(chunk) + encryptor.finalize()
            encrypted_chunks.append((ciphertext, iv, encryptor.tag))

        return encrypted_chunks

    def decrypt_large_data(
        self, encrypted_chunks: List[Tuple[bytes, bytes, bytes]], key: bytes
    ) -> bytes:
        """
        대용량 데이터를 청크 단위로 복호화

        Args:
            encrypted_chunks: 암호화된 청크 리스트
            key: 복호화 키

        Returns:
            bytes: 복호화된 데이터
        """
        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")

        decrypted_data = b""

        for i, (ciphertext, iv, tag) in enumerate(encrypted_chunks):
            cipher = Cipher(
                algorithms.AES(key), modes.GCM(iv, tag), backend=self.backend
            )
            decryptor = cipher.decryptor()

            # 청크 번호를 AAD로 사용
            chunk_info = f"chunk:{i}:total:{len(encrypted_chunks)}"
            decryptor.authenticate_additional_data(chunk_info.encode("utf-8"))

            try:
                chunk_data = decryptor.update(ciphertext) + decryptor.finalize()
                decrypted_data += chunk_data
            except InvalidTag:
                raise InvalidTag(f"청크 {i}의 인증 실패")

        return decrypted_data


def demonstrate_security_best_practices():
    """보안 모범 사례 데모"""
    print("=" * 60)
    print("AES 보안 모범 사례 데모")
    print("=" * 60)

    secure_aes = SecureAESManager(key_length=256)

    # 1. 안전한 키 생성
    print("1. 안전한 키 생성")
    key = secure_aes.generate_secure_key()
    print(f"생성된 키 길이: {len(key)} 바이트")
    print(f"키 (hex): {key.hex()}")

    # 2. 비밀번호 강도 검증
    print("\n2. 비밀번호 강도 검증")
    weak_passwords = ["123456", "password", "abc123", "MyPassword123!@#"]

    for pwd in weak_passwords:
        is_secure = secure_aes.validate_password(pwd)
        print(f"'{pwd}': {'안전함' if is_secure else '취약함'}")

    # 3. 안전한 키 유도
    print("\n3. 안전한 키 유도")
    strong_password = "MySecurePassword123!@#"
    try:
        derived_key, salt = secure_aes.derive_key_securely(strong_password)
        print(f"비밀번호: {strong_password}")
        print(f"유도된 키 (hex): {derived_key.hex()}")
        print(f"솔트 (hex): {salt.hex()}")
    except ValueError as e:
        print(f"오류: {e}")

    # 4. 인증이 포함된 암호화
    print("\n4. 인증이 포함된 암호화")
    sensitive_data = "이것은 매우 중요한 데이터입니다!"
    metadata = "user_id:12345,created:2024-01-01"

    ciphertext, iv, tag = secure_aes.encrypt_with_authentication(
        sensitive_data, key, metadata
    )
    print(f"원본 데이터: {sensitive_data}")
    print(f"메타데이터: {metadata}")
    print(f"암호문 길이: {len(ciphertext)} 바이트")

    # 5. 안전한 복호화
    print("\n5. 안전한 복호화")
    try:
        decrypted = secure_aes.decrypt_with_authentication(
            ciphertext, key, iv, tag, metadata
        )
        print(f"복호화 성공: {sensitive_data == decrypted}")
        print(f"복호화된 데이터: {decrypted}")
    except InvalidTag as e:
        print(f"인증 실패: {e}")


def demonstrate_large_data_encryption():
    """대용량 데이터 암호화 데모"""
    print("\n" + "=" * 60)
    print("대용량 데이터 암호화 데모")
    print("=" * 60)

    secure_aes = SecureAESManager(key_length=256)
    key = secure_aes.generate_secure_key()

    # 대용량 데이터 생성 (1MB)
    large_data = b"A" * (1024 * 1024)  # 1MB
    print(f"원본 데이터 크기: {len(large_data)} 바이트")

    # 청크 단위로 암호화
    print("\n청크 단위로 암호화 중...")
    encrypted_chunks = secure_aes.encrypt_large_data(large_data, key, chunk_size=1024)
    print(f"암호화된 청크 수: {len(encrypted_chunks)}")

    # 청크 단위로 복호화
    print("청크 단위로 복호화 중...")
    decrypted_data = secure_aes.decrypt_large_data(encrypted_chunks, key)
    print(f"복호화된 데이터 크기: {len(decrypted_data)} 바이트")
    print(f"복호화 성공: {large_data == decrypted_data}")


def demonstrate_timing_attack_prevention():
    """타이밍 공격 방어 데모"""
    print("\n" + "=" * 60)
    print("타이밍 공격 방어 데모")
    print("=" * 60)

    import time

    def constant_time_compare(a: bytes, b: bytes) -> bool:
        """
        상수 시간 비교 (타이밍 공격 방어)

        Args:
            a: 비교할 바이트열 1
            b: 비교할 바이트열 2

        Returns:
            bool: 두 바이트열이 같은지 여부
        """
        if len(a) != len(b):
            return False

        result = 0
        for x, y in zip(a, b):
            result |= x ^ y

        return result == 0

    # 테스트 데이터
    data1 = b"Hello World"
    data2 = b"Hello World"
    data3 = b"Hello World!"

    print("상수 시간 비교 테스트:")
    print(
        f"'{data1.decode()}' == '{data2.decode()}': {constant_time_compare(data1, data2)}"
    )
    print(
        f"'{data1.decode()}' == '{data3.decode()}': {constant_time_compare(data1, data3)}"
    )

    # 타이밍 측정
    print("\n타이밍 측정:")

    # 같은 데이터 비교
    start_time = time.perf_counter()
    for _ in range(1000):
        constant_time_compare(data1, data2)
    same_time = time.perf_counter() - start_time

    # 다른 데이터 비교
    start_time = time.perf_counter()
    for _ in range(1000):
        constant_time_compare(data1, data3)
    different_time = time.perf_counter() - start_time

    print(f"같은 데이터 비교 시간: {same_time:.6f}초")
    print(f"다른 데이터 비교 시간: {different_time:.6f}초")
    print(f"시간 차이: {abs(same_time - different_time):.6f}초")


def demonstrate_key_rotation():
    """키 로테이션 데모"""
    print("\n" + "=" * 60)
    print("키 로테이션 데모")
    print("=" * 60)

    secure_aes = SecureAESManager(key_length=256)

    # 현재 키와 새 키 생성
    current_key = secure_aes.generate_secure_key()
    new_key = secure_aes.generate_secure_key()

    print(f"현재 키 (hex): {current_key.hex()}")
    print(f"새 키 (hex): {new_key.hex()}")

    # 데이터를 현재 키로 암호화
    data = "중요한 데이터"
    ciphertext, iv, tag = secure_aes.encrypt_with_authentication(data, current_key)
    print(f"현재 키로 암호화 완료")

    # 현재 키로 복호화 (정상)
    try:
        decrypted = secure_aes.decrypt_with_authentication(
            ciphertext, current_key, iv, tag
        )
        print(f"현재 키로 복호화 성공: {data == decrypted}")
    except InvalidTag as e:
        print(f"복호화 실패: {e}")

    # 새 키로 복호화 시도 (실패해야 함)
    try:
        decrypted = secure_aes.decrypt_with_authentication(ciphertext, new_key, iv, tag)
        print(f"새 키로 복호화 성공: {data == decrypted}")
    except InvalidTag as e:
        print(f"새 키로 복호화 실패 (예상됨): {e}")

    # 키 로테이션: 데이터를 새 키로 재암호화
    print("\n키 로테이션 수행:")
    new_ciphertext, new_iv, new_tag = secure_aes.encrypt_with_authentication(
        data, new_key
    )
    print(f"새 키로 재암호화 완료")

    # 새 키로 복호화
    try:
        decrypted = secure_aes.decrypt_with_authentication(
            new_ciphertext, new_key, new_iv, new_tag
        )
        print(f"새 키로 복호화 성공: {data == decrypted}")
    except InvalidTag as e:
        print(f"복호화 실패: {e}")


def demonstrate_secure_storage():
    """안전한 저장 데모"""
    print("\n" + "=" * 60)
    print("안전한 저장 데모")
    print("=" * 60)

    secure_aes = SecureAESManager(key_length=256)

    # 사용자 데이터
    user_data = {
        "user_id": "12345",
        "email": "user@example.com",
        "sensitive_info": "개인정보",
    }

    print(f"원본 사용자 데이터: {user_data}")

    # 데이터를 JSON으로 직렬화
    import json

    json_data = json.dumps(user_data, ensure_ascii=False)
    print(f"JSON 데이터: {json_data}")

    # 암호화
    key = secure_aes.generate_secure_key()
    ciphertext, iv, tag = secure_aes.encrypt_with_authentication(json_data, key)

    # 저장 시뮬레이션 (실제로는 안전한 저장소 사용)
    stored_data = {
        "ciphertext": ciphertext.hex(),
        "iv": iv.hex(),
        "tag": tag.hex(),
        "algorithm": "AES-256-GCM",
    }

    print(f"\n저장된 데이터 (hex):")
    for k, v in stored_data.items():
        print(f"  {k}: {v}")

    # 복호화
    try:
        decrypted_json = secure_aes.decrypt_with_authentication(
            bytes.fromhex(stored_data["ciphertext"]),
            key,
            bytes.fromhex(stored_data["iv"]),
            bytes.fromhex(stored_data["tag"]),
        )

        decrypted_data = json.loads(decrypted_json)
        print(f"\n복호화된 데이터: {decrypted_data}")
        print(f"복호화 성공: {user_data == decrypted_data}")

    except (InvalidTag, json.JSONDecodeError) as e:
        print(f"복호화 실패: {e}")


def main():
    """메인 함수 - 모든 보안 데모 실행"""
    print("AES 보안 모범 사례 종합 데모")
    print("=" * 60)
    print("이 데모는 AES 암호화의 보안 측면을 보여줍니다:")
    print("1. 보안 모범 사례")
    print("2. 대용량 데이터 암호화")
    print("3. 타이밍 공격 방어")
    print("4. 키 로테이션")
    print("5. 안전한 저장")
    print("=" * 60)

    try:
        demonstrate_security_best_practices()
        demonstrate_large_data_encryption()
        demonstrate_timing_attack_prevention()
        demonstrate_key_rotation()
        demonstrate_secure_storage()

        print("\n" + "=" * 60)
        print("모든 보안 데모가 성공적으로 완료되었습니다!")
        print("=" * 60)

    except Exception as e:
        print(f"\n오류 발생: {e}")
        print("필요한 패키지를 설치하세요: pip install cryptography")


if __name__ == "__main__":
    main()
