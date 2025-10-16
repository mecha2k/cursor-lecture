#!/usr/bin/env python3
"""
AES 암호화/복호화 기초부터 고급까지
====================================

이 파일은 AES(Advanced Encryption Standard) 암호화에 대한
기초부터 고급 사용법까지 상세히 설명하고 예제를 제공합니다.

AES란?
- 미국 NIST에서 공식 채택한 대칭키 암호화 알고리즘
- 128, 192, 256비트 키 길이 지원
- 블록 크기: 128비트 (16바이트)
- 현재 가장 널리 사용되는 대칭키 암호화 표준

주요 특징:
- 빠른 암호화/복호화 속도
- 하드웨어 가속 지원
- 다양한 운영 모드 지원 (CBC, GCM, CTR 등)
- 안전성 검증된 알고리즘
"""

import os
import base64
import hashlib
import secrets
from typing import Tuple, Optional, Union
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidKey, InvalidTag


class AESEncryption:
    """
    AES 암호화/복호화를 위한 클래스

    이 클래스는 다양한 AES 운영 모드를 지원하며,
    보안 모범 사례를 따릅니다.
    """

    def __init__(self, key_length: int = 256):
        """
        AES 암호화 객체 초기화

        Args:
            key_length: 키 길이 (128, 192, 256 중 선택)
        """
        if key_length not in [128, 192, 256]:
            raise ValueError("키 길이는 128, 192, 256 중 하나여야 합니다")

        self.key_length = key_length
        self.key_bytes = key_length // 8  # 비트를 바이트로 변환
        self.backend = default_backend()

    def generate_key(self) -> bytes:
        """
        암호학적으로 안전한 랜덤 키 생성

        Returns:
            bytes: 생성된 키
        """
        return secrets.token_bytes(self.key_bytes)

    def derive_key_from_password(
        self, password: str, salt: Optional[bytes] = None
    ) -> Tuple[bytes, bytes]:
        """
        비밀번호에서 키 유도 (PBKDF2 사용)

        Args:
            password: 사용자 비밀번호
            salt: 솔트 (None이면 자동 생성)

        Returns:
            Tuple[bytes, bytes]: (유도된 키, 사용된 솔트)
        """
        if salt is None:
            salt = secrets.token_bytes(16)  # 128비트 솔트

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.key_bytes,
            salt=salt,
            iterations=100000,  # 보안을 위해 높은 반복 횟수
            backend=self.backend,
        )

        key = kdf.derive(password.encode("utf-8"))
        return key, salt

    def encrypt_cbc(self, plaintext: str, key: bytes) -> Tuple[bytes, bytes]:
        """
        CBC 모드로 AES 암호화

        CBC (Cipher Block Chaining):
        - 각 블록이 이전 블록의 암호문과 XOR
        - 초기화 벡터(IV) 필요
        - 패딩 필요 (PKCS7)

        Args:
            plaintext: 암호화할 평문
            key: 암호화 키

        Returns:
            Tuple[bytes, bytes]: (암호문, IV)
        """
        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")

        # 초기화 벡터 생성 (랜덤)
        iv = secrets.token_bytes(16)  # AES 블록 크기

        # 패딩 추가
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext.encode("utf-8"))
        padded_data += padder.finalize()

        # 암호화
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        return ciphertext, iv

    def decrypt_cbc(self, ciphertext: bytes, key: bytes, iv: bytes) -> str:
        """
        CBC 모드로 AES 복호화

        Args:
            ciphertext: 암호문
            key: 복호화 키
            iv: 초기화 벡터

        Returns:
            str: 복호화된 평문
        """
        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")

        if len(iv) != 16:
            raise ValueError("IV 길이가 16바이트여야 합니다")

        # 복호화
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=self.backend)
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()

        # 패딩 제거
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data)
        data += unpadder.finalize()

        return data.decode("utf-8")

    def encrypt_gcm(self, plaintext: str, key: bytes) -> Tuple[bytes, bytes, bytes]:
        """
        GCM 모드로 AES 암호화 (인증 포함)

        GCM (Galois/Counter Mode):
        - 인증과 암호화를 동시에 제공
        - 추가 인증 데이터(AAD) 지원
        - 패딩 불필요
        - 무결성 검증 자동 수행

        Args:
            plaintext: 암호화할 평문
            key: 암호화 키

        Returns:
            Tuple[bytes, bytes, bytes]: (암호문, IV, 태그)
        """
        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")

        # 초기화 벡터 생성
        iv = secrets.token_bytes(12)  # GCM 권장 IV 길이

        # 암호화
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=self.backend)
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(plaintext.encode("utf-8")) + encryptor.finalize()

        return ciphertext, iv, encryptor.tag

    def decrypt_gcm(self, ciphertext: bytes, key: bytes, iv: bytes, tag: bytes) -> str:
        """
        GCM 모드로 AES 복호화 (인증 검증 포함)

        Args:
            ciphertext: 암호문
            key: 복호화 키
            iv: 초기화 벡터
            tag: 인증 태그

        Returns:
            str: 복호화된 평문

        Raises:
            InvalidTag: 인증 태그 검증 실패
        """
        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")

        if len(iv) != 12:
            raise ValueError("IV 길이가 12바이트여야 합니다")

        # 복호화
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=self.backend)
        decryptor = cipher.decryptor()

        try:
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            return plaintext.decode("utf-8")
        except InvalidTag:
            raise InvalidTag("인증 태그 검증 실패 - 데이터가 변조되었을 수 있습니다")

    def encrypt_with_aad(
        self, plaintext: str, key: bytes, additional_data: str = ""
    ) -> Tuple[bytes, bytes, bytes]:
        """
        추가 인증 데이터(AAD)와 함께 GCM 암호화

        Args:
            plaintext: 암호화할 평문
            key: 암호화 키
            additional_data: 추가 인증 데이터

        Returns:
            Tuple[bytes, bytes, bytes]: (암호문, IV, 태그)
        """
        if len(key) != self.key_bytes:
            raise ValueError(f"키 길이가 {self.key_bytes}바이트여야 합니다")

        iv = secrets.token_bytes(12)

        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=self.backend)
        encryptor = cipher.encryptor()

        # AAD 추가
        if additional_data:
            encryptor.authenticate_additional_data(additional_data.encode("utf-8"))

        ciphertext = encryptor.update(plaintext.encode("utf-8")) + encryptor.finalize()

        return ciphertext, iv, encryptor.tag

    def decrypt_with_aad(
        self,
        ciphertext: bytes,
        key: bytes,
        iv: bytes,
        tag: bytes,
        additional_data: str = "",
    ) -> str:
        """
        추가 인증 데이터(AAD)와 함께 GCM 복호화

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

        if len(iv) != 12:
            raise ValueError("IV 길이가 12바이트여야 합니다")

        cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=self.backend)
        decryptor = cipher.decryptor()

        # AAD 추가
        if additional_data:
            decryptor.authenticate_additional_data(additional_data.encode("utf-8"))

        try:
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            return plaintext.decode("utf-8")
        except InvalidTag:
            raise InvalidTag(
                "인증 실패 - 데이터가 변조되었거나 AAD가 일치하지 않습니다"
            )

# "107ade7f090d4ad398eeedb5b0b9a66b746942aaeda79bfbadd8532f5589f165"
def demonstrate_basic_encryption():
    """기본 AES 암호화/복호화 데모"""
    print("=" * 60)
    print("기본 AES 암호화/복호화 데모")
    print("=" * 60)

    # AES 객체 생성 (256비트 키)
    aes = AESEncryption(key_length=256)

    # 키 생성
    key = aes.generate_key()
    print(f"생성된 키 (hex): {key.hex()}")
    print(f"키 길이: {len(key)} 바이트")

    # 평문
    plaintext = "안녕하세요! 이것은 AES 암호화 테스트입니다. 🔐"
    print(f"\n원본 평문: {plaintext}")

    # CBC 모드 암호화
    print("\n--- CBC 모드 암호화 ---")
    ciphertext_cbc, iv_cbc = aes.encrypt_cbc(plaintext, key)
    print(f"암호문 (hex): {ciphertext_cbc.hex()}")
    print(f"IV (hex): {iv_cbc.hex()}")

    # CBC 모드 복호화
    decrypted_cbc = aes.decrypt_cbc(ciphertext_cbc, key, iv_cbc)
    print(f"복호화된 평문: {decrypted_cbc}")
    print(f"복호화 성공: {plaintext == decrypted_cbc}")

    # GCM 모드 암호화
    print("\n--- GCM 모드 암호화 (인증 포함) ---")
    ciphertext_gcm, iv_gcm, tag_gcm = aes.encrypt_gcm(plaintext, key)
    print(f"암호문 (hex): {ciphertext_gcm.hex()}")
    print(f"IV (hex): {iv_gcm.hex()}")
    print(f"태그 (hex): {tag_gcm.hex()}")

    # GCM 모드 복호화
    decrypted_gcm = aes.decrypt_gcm(ciphertext_gcm, key, iv_gcm, tag_gcm)
    print(f"복호화된 평문: {decrypted_gcm}")
    print(f"복호화 성공: {plaintext == decrypted_gcm}")


def demonstrate_password_based_encryption():
    """비밀번호 기반 암호화 데모"""
    print("\n" + "=" * 60)
    print("비밀번호 기반 AES 암호화 데모")
    print("=" * 60)

    aes = AESEncryption(key_length=256)

    # 사용자 비밀번호
    password = "MySecurePassword123!@#"
    print(f"사용자 비밀번호: {password}")

    # 비밀번호에서 키 유도
    key, salt = aes.derive_key_from_password(password)
    print(f"유도된 키 (hex): {key.hex()}")
    print(f"사용된 솔트 (hex): {salt.hex()}")

    # 암호화할 데이터
    sensitive_data = "이것은 매우 중요한 개인정보입니다!"
    print(f"\n암호화할 데이터: {sensitive_data}")

    # GCM 모드로 암호화 (인증 포함)
    ciphertext, iv, tag = aes.encrypt_gcm(sensitive_data, key)
    print(f"암호문 (hex): {ciphertext.hex()}")

    # 복호화
    decrypted = aes.decrypt_gcm(ciphertext, key, iv, tag)
    print(f"복호화된 데이터: {decrypted}")
    print(f"복호화 성공: {sensitive_data == decrypted}")


def demonstrate_aad_encryption():
    """추가 인증 데이터(AAD)를 사용한 암호화 데모"""
    print("\n" + "=" * 60)
    print("추가 인증 데이터(AAD) 암호화 데모")
    print("=" * 60)

    aes = AESEncryption(key_length=256)
    key = aes.generate_key()

    # 메타데이터 (AAD)
    metadata = "user_id:12345,timestamp:2024-01-01,version:1.0"
    print(f"추가 인증 데이터: {metadata}")

    # 실제 데이터
    user_data = "사용자의 개인정보와 중요한 데이터"
    print(f"암호화할 데이터: {user_data}")

    # AAD와 함께 암호화
    ciphertext, iv, tag = aes.encrypt_with_aad(user_data, key, metadata)
    print(f"암호문 (hex): {ciphertext.hex()}")

    # 올바른 AAD로 복호화
    print("\n--- 올바른 AAD로 복호화 ---")
    decrypted_correct = aes.decrypt_with_aad(ciphertext, key, iv, tag, metadata)
    print(f"복호화 성공: {user_data == decrypted_correct}")
    print(f"복호화된 데이터: {decrypted_correct}")

    # 잘못된 AAD로 복호화 시도
    print("\n--- 잘못된 AAD로 복호화 시도 ---")
    wrong_metadata = "user_id:99999,timestamp:2024-01-01,version:1.0"
    print(f"잘못된 AAD: {wrong_metadata}")

    try:
        decrypted_wrong = aes.decrypt_with_aad(ciphertext, key, iv, tag, wrong_metadata)
        print(f"복호화 결과: {decrypted_wrong}")
    except InvalidTag as e:
        print(f"인증 실패: {e}")


def demonstrate_tamper_detection():
    """데이터 변조 탐지 데모"""
    print("\n" + "=" * 60)
    print("데이터 변조 탐지 데모")
    print("=" * 60)

    aes = AESEncryption(key_length=256)
    key = aes.generate_key()

    original_data = "이 데이터는 변조되어서는 안 됩니다!"
    print(f"원본 데이터: {original_data}")

    # GCM 모드로 암호화 (무결성 보장)
    ciphertext, iv, tag = aes.encrypt_gcm(original_data, key)
    print(f"암호문 (hex): {ciphertext.hex()}")

    # 정상적인 복호화
    print("\n--- 정상적인 복호화 ---")
    try:
        decrypted = aes.decrypt_gcm(ciphertext, key, iv, tag)
        print(f"복호화 성공: {decrypted}")
    except InvalidTag as e:
        print(f"인증 실패: {e}")

    # 데이터 변조 시도
    print("\n--- 데이터 변조 시도 ---")
    tampered_ciphertext = bytearray(ciphertext)
    tampered_ciphertext[0] = (tampered_ciphertext[0] + 1) % 256  # 1바이트 변경
    print(f"변조된 암호문 (hex): {bytes(tampered_ciphertext).hex()}")

    try:
        decrypted_tampered = aes.decrypt_gcm(bytes(tampered_ciphertext), key, iv, tag)
        print(f"복호화 결과: {decrypted_tampered}")
    except InvalidTag as e:
        print(f"변조 탐지됨: {e}")


def demonstrate_key_management():
    """키 관리 모범 사례 데모"""
    print("\n" + "=" * 60)
    print("키 관리 모범 사례 데모")
    print("=" * 60)

    aes = AESEncryption(key_length=256)

    # 1. 안전한 키 생성
    print("1. 안전한 키 생성")
    key1 = aes.generate_key()
    key2 = aes.generate_key()
    print(f"키1 (hex): {key1.hex()}")
    print(f"키2 (hex): {key2.hex()}")
    print(f"키가 다름: {key1 != key2}")

    # 2. 비밀번호 기반 키 유도
    print("\n2. 비밀번호 기반 키 유도")
    password = "UserPassword123!"
    key_from_password, salt = aes.derive_key_from_password(password)
    print(f"비밀번호: {password}")
    print(f"유도된 키 (hex): {key_from_password.hex()}")
    print(f"솔트 (hex): {salt.hex()}")

    # 3. 같은 비밀번호, 다른 솔트로 키 유도
    print("\n3. 같은 비밀번호, 다른 솔트로 키 유도")
    key_from_password2, salt2 = aes.derive_key_from_password(password)
    print(f"새로운 솔트 (hex): {salt2.hex()}")
    print(f"유도된 키가 다름: {key_from_password != key_from_password2}")

    # 4. 키 저장 및 로드 시뮬레이션
    print("\n4. 키 저장 및 로드 시뮬레이션")
    # 실제 환경에서는 안전한 키 저장소 사용
    stored_key = key_from_password
    stored_salt = salt

    # 데이터 암호화
    data = "저장할 중요한 데이터"
    ciphertext, iv, tag = aes.encrypt_gcm(data, stored_key)
    print(f"암호화된 데이터 저장됨")

    # 나중에 키와 솔트로 복호화
    loaded_key, _ = aes.derive_key_from_password(password, stored_salt)
    decrypted = aes.decrypt_gcm(ciphertext, loaded_key, iv, tag)
    print(f"복호화 성공: {data == decrypted}")


def demonstrate_performance_comparison():
    """성능 비교 데모"""
    print("\n" + "=" * 60)
    print("AES 키 길이별 성능 비교")
    print("=" * 60)

    import time

    # 테스트 데이터
    test_data = "A" * 1000  # 1KB 데이터

    key_lengths = [128, 192, 256]

    for key_length in key_lengths:
        print(f"\n--- {key_length}비트 키 테스트 ---")
        aes = AESEncryption(key_length=key_length)
        key = aes.generate_key()

        # 암호화 시간 측정
        start_time = time.time()
        ciphertext, iv, tag = aes.encrypt_gcm(test_data, key)
        encrypt_time = time.time() - start_time

        # 복호화 시간 측정
        start_time = time.time()
        decrypted = aes.decrypt_gcm(ciphertext, key, iv, tag)
        decrypt_time = time.time() - start_time

        print(f"암호화 시간: {encrypt_time:.6f}초")
        print(f"복호화 시간: {decrypt_time:.6f}초")
        print(f"총 시간: {encrypt_time + decrypt_time:.6f}초")
        print(f"복호화 성공: {test_data == decrypted}")


def main():
    """메인 함수 - 모든 데모 실행"""
    print("AES 암호화/복호화 종합 데모")
    print("=" * 60)
    print("이 데모는 AES 암호화의 다양한 측면을 보여줍니다:")
    print("1. 기본 암호화/복호화")
    print("2. 비밀번호 기반 암호화")
    print("3. 추가 인증 데이터 사용")
    print("4. 데이터 변조 탐지")
    print("5. 키 관리 모범 사례")
    print("6. 성능 비교")
    print("=" * 60)

    try:
        # 모든 데모 실행
        demonstrate_basic_encryption()
        demonstrate_password_based_encryption()
        demonstrate_aad_encryption()
        demonstrate_tamper_detection()
        demonstrate_key_management()
        demonstrate_performance_comparison()

        print("\n" + "=" * 60)
        print("모든 데모가 성공적으로 완료되었습니다!")
        print("=" * 60)

    except Exception as e:
        print(f"\n오류 발생: {e}")


if __name__ == "__main__":
    main()
