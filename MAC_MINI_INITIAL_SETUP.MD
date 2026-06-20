# 🖥️ Mac Mini 초기 세팅 가이드

> Cursor 설치 전까지 수동으로 완료해야 하는 항목  
> 이 과정이 끝나면 Cursor에서 `MAC_MINI_SERVER.MD`를 열고 나머지를 자동 구축 요청

---

## Phase 0 — macOS 최초 부팅 설정

macOS 설정 어시스턴트에서 진행:

- [ ] 언어: 한국어 (또는 선호 언어)
- [ ] Apple ID 로그인 (선택 — 앱스토어 사용 시 필요)
- [ ] 위치 서비스: 필요 시 활성화
- [ ] Siri: 비활성화 권장 (서버 용도)
- [ ] 스크린 타임: 비활성화

---

## Phase 1 — 기본 시스템 설정

### 1-1. 자동 로그인 설정

서버는 재부팅 후 사람 없이도 자동으로 로그인되어야 합니다.

```
시스템 설정 → 일반 → 사용자 및 그룹
→ 자동 로그인 → 사용할 계정 선택
```

> FileVault가 켜져 있으면 자동 로그인이 비활성화됩니다.  
> 홈서버 용도라면 FileVault 비활성화 권장 (시스템 설정 → 개인 정보 보호 및 보안 → FileVault)

---

### 1-2. 절전 방지 설정 (24시간 상시 가동)

```
시스템 설정 → 에너지 절약
→ 다음 이후 디스플레이 끄기: 안 함
→ 하드 디스크를 가능하면 절전 모드로 전환: 끄기
→ 네트워크 액세스가 허용되면 깨우기: 켜기
```

터미널에서도 설정 가능:

```bash
# 디스플레이 & 시스템 절전 모두 해제
sudo pmset -a sleep 0
sudo pmset -a displaysleep 0
sudo pmset -a disksleep 0
sudo pmset -a womp 1       # 네트워크 Wake-on-LAN 활성화

# 설정 확인
pmset -g
```

---

### 1-3. SSH 원격 접속 활성화

```
시스템 설정 → 일반 → 공유
→ 원격 로그인: 켜기
→ 허용 대상: 모든 사용자 (또는 특정 사용자)
```

터미널에서 활성화:

```bash
sudo systemsetup -setremotelogin on
```

활성화 확인 (다른 기기에서 테스트):

```bash
ssh 유저명@맥미니-로컬IP
```

---

### 1-4. 화면 공유 활성화

원격에서 GUI 화면 제어가 필요할 때 사용합니다.

```
시스템 설정 → 일반 → 공유
→ 화면 공유: 켜기
```

---

### 1-5. 컴퓨터 이름 설정

네트워크에서 구분하기 쉽도록 이름을 지정합니다.

```
시스템 설정 → 일반 → 공유
→ 로컬 호스트 이름: macmini (원하는 이름)
```

또는 터미널에서:

```bash
sudo scutil --set HostName macmini
sudo scutil --set LocalHostName macmini
sudo scutil --set ComputerName macmini
```

---

## Phase 2 — 외장 드라이브 설정

### 2-1. 볼륨 이름 고정

재부팅 후 마운트 경로(`/Volumes/SSD1`)가 바뀌지 않도록 이름을 고정합니다.

```
디스크 유틸리티 앱 실행
→ 외장 SSD 선택 → 마운트된 볼륨 클릭
→ 상단 메뉴: 편집 → 이름 변경
→ SSD1 (미디어용), SSD2 (백업용)
```

### 2-2. 자동 마운트 설정

```
시스템 설정 → 일반 → 로그인 항목
→ 하단 '+' 버튼 → 외장 드라이브 선택하여 추가
```

재부팅 후 `/Volumes/SSD1`, `/Volumes/SSD2` 경로 유지 확인:

```bash
ls /Volumes/
```

---

## Phase 3 — 필수 소프트웨어 설치

### 3-1. Homebrew 설치

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Apple Silicon(M 시리즈) Mac에서 PATH 추가:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

# 설치 확인
brew --version
```

---

### 3-2. Tailscale 설치 및 연결

원격지에서 Mac Mini에 안전하게 접속하기 위한 VPN입니다.  
이 단계를 완료하면 집 밖에서도 SSH로 접속하여 나머지 작업을 진행할 수 있습니다.

```bash
brew install --cask tailscale
```

설치 후:

```
앱 실행 → 메뉴바 Tailscale 아이콘 클릭
→ Log in → 계정 로그인 (Google/GitHub 등)
```

연결 확인:

```bash
# Tailscale IP 확인 (100.x.x.x 형태)
tailscale ip -4
```

> 이 IP를 메모해두면 외부에서 `ssh 유저명@100.x.x.x` 로 접속 가능

---

### 3-3. Cursor 설치

```bash
brew install --cask cursor
```

---

### 3-4. Git 설치 및 설정

```bash
brew install git

git config --global user.name "이름"
git config --global user.email "이메일"
```

---

## Phase 4 — Cursor로 이관

여기까지 완료됐으면 나머지는 Cursor에서 진행합니다.

### 이관 방법

1. Cursor 실행
2. `MAC_MINI_SERVER.MD` 파일 열기
3. 아래 프롬프트로 구축 시작 요청:

```
이 설계 문서를 기반으로 Phase 1(웹 서버/Docker 기반)부터 실제 구축을 시작해줘.
각 단계를 실행하고 결과를 확인한 뒤 다음 단계로 넘어가도록 해줘.
오류 발생 시 바로 수정하고 계속 진행해줘.
```

---

## 빠른 완료 체크리스트


| 단계  | 항목                                     | 완료  |
| --- | -------------------------------------- | --- |
| 0   | macOS 최초 부팅 설정                         | [ ] |
| 1-1 | 자동 로그인 설정                              | [ ] |
| 1-2 | 절전 방지 (`pmset`)                        | [ ] |
| 1-3 | SSH 원격 로그인 활성화                         | [ ] |
| 1-4 | 화면 공유 활성화                              | [ ] |
| 1-5 | 컴퓨터 이름 설정                              | [ ] |
| 2-1 | 외장 SSD 볼륨 이름 고정 (`SSD1`, `SSD2`)       | [ ] |
| 2-2 | 외장 SSD 자동 마운트 등록                       | [ ] |
| 3-1 | Homebrew 설치                            | [ ] |
| 3-2 | Tailscale 설치 및 계정 연결                   | [ ] |
| 3-3 | Cursor 설치                              | [ ] |
| 3-4 | Git 설치 및 설정                            | [ ] |
| 4   | Cursor에서 `MAC_MINI_SERVER.MD` 열고 구축 시작 | [ ] |


---

> 예상 소요 시간: **30~40분**  
> 이후 Docker · Cloudflare · AI 비서 등 나머지 구축은 Cursor가 진행

