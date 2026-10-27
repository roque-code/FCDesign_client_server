# Bitácora de instalación del servidor en AWS

Esta bitácora recorre los cambios de la instancia `cfdesign` desde la primera configuración, el 20 y 21 de octubre de 2026, hasta el sitio en `https://fcdesign.aulivana.com` el 26 de octubre. Sirve para repetir la instalación en otra EC2: se siguen las entradas en orden y se usan los valores de la última, no las IP que ya se soltaron.

El procedimiento del estado final, con el detalle de consola, está en [instalacion-aws.md](instalacion-aws.md). El Word de esta bitácora está en [Bitacora-instalacion-AWS.docx](Bitacora-instalacion-AWS.docx).

No se anotan contraseñas. La de Gmail, la de Django y el archivo `cfdesign.pem` se copian aparte. `.env` no se sube a Git.

## Estado al que se llega

| Dato | Valor que se replica |
| --- | --- |
| Región | Ohio, `us-east-2` |
| Instancia de referencia | `cfdesign`, `i-07c39f84b1c7b3787` |
| Tipo | `t3.small` |
| Sistema | Amazon Linux 2023, x86_64, IMDSv2 obligatorio |
| VPC / subred | `vpc-0877ce6fabe7f919f` / `subnet-0065e8a11b4f527d8` |
| IP privada | `172.31.24.67` en esta instancia. En una nueva, la que asigne la subred |
| IP pública | Elástica. El 26 de octubre de 2026 es `77.112.213.200` |
| Nombre | `fcdesign.aulivana.com`, registro A en GoDaddy |
| Grupo de seguridad | `launch-wizard-1`, `sg-05d3ffa45265dcd67` |
| Puertos de entrada | 22, 80 y 443. Sin 18080 y sin 8025 |
| Disco | 30 GB, sistema de archivos estirado con `growpart` y `xfs_growfs` |
| Arranque | `compose.servidor.yaml`, `config.settings.production`, certificado Let's Encrypt |
| Correo | Gmail, `smtp.gmail.com:587`. Sin Mailpit |
| Código en la EC2 | `~/fcdesign/FCDesign_client_server` |

## 1. Primera instancia, 20 y 21 de octubre

Se creó la EC2 en Ohio con Amazon Linux 2023, tipo `t3.micro`, par de claves `cfdesign`, IP pública automática `18.118.112.206` e IP privada `172.31.24.67`. El grupo que quedó pegado a la instancia es `launch-wizard-1`, no el grupo `default`.

En la instancia, Amazon Linux no tiene `apt-get`. El gestor es `dnf`.

```bash
sudo dnf update -y
sudo dnf install -y git docker
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
```

Hay que salir y volver a entrar por SSH. Después, Compose 2.40.3 y Buildx 0.38.0. Sin ese Buildx, `docker compose build` no corre. La máquina es x86_64, así que los binarios son `linux-amd64` y `linux-x86_64`.

```bash
sudo mkdir -p /usr/libexec/docker/cli-plugins
sudo curl -SL "https://github.com/docker/compose/releases/download/v2.40.3/docker-compose-linux-x86_64" -o /usr/libexec/docker/cli-plugins/docker-compose
sudo chmod +x /usr/libexec/docker/cli-plugins/docker-compose
mkdir -p ~/.docker/cli-plugins
curl -SL "https://github.com/docker/buildx/releases/download/v0.38.0/buildx-v0.38.0.linux-amd64" -o ~/.docker/cli-plugins/docker-buildx
chmod +x ~/.docker/cli-plugins/docker-buildx
```

Se creó una clave SSH solo de lectura para GitHub y se clonó el repositorio en `~/fcdesign/FCDesign_client_server`. El archivo que arranca el servidor es `compose.servidor.yaml`. `docker compose` sin `-f` lee `compose.yaml`, que es el de desarrollo, y no se usa aquí.

En ese primer arranque el sitio era HTTP en el puerto 18080, Django cargaba `config.settings.development` y el correo salía por Gmail. El `.env` llevaba `DJANGO_SECRET_KEY`, `EMAIL_HOST_PASSWORD` y el origen `http://18.118.112.206:18080`. La contraseña de aplicación de Gmail no se escribe en el repositorio.

El grupo `default` también tenía el 18080, pero la instancia no lo usa. La regla que abrió el sitio fue la de `launch-wizard-1`. El navegador entró en `http://18.118.112.206:18080`. El puerto 8080 no estaba abierto.

En el `t3.micro`, la construcción de imágenes se quedó sin memoria y la sesión SSH se cortó. Antes de construir se dejó un intercambio de 2 GB:

```bash
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Para repetir esta entrada en una instancia nueva se conservan el sistema, la región, la subred, la clave, Docker, Compose, Buildx, el clon y el intercambio. No se conserva el puerto 18080 ni el modo desarrollo: eso lo sustituye la entrada 6.

## 2. Quitar Vite del servidor, 25 de octubre

El contenedor `frontend` servía la página con Vite y gastaba memoria en la micro. El commit `se evita usar vite em el servidor` deja la página construida dentro de la imagen de Nginx (`deploy/nginx.servidor.Dockerfile` y `deploy/nginx/servidor.conf`).

En la EC2, después de `git pull origin main`:

```bash
cd ~/fcdesign/FCDesign_client_server
docker compose -f compose.servidor.yaml build web
docker compose -f compose.servidor.yaml build runner
docker compose -f compose.servidor.yaml build nginx
docker compose -f compose.servidor.yaml up -d --remove-orphans
```

`--remove-orphans` apaga el contenedor `frontend` si quedó de un arranque anterior. No se usa `down -v`: eso borra `traza-db` y `traza-redis`.

Si `git pull` se detiene porque un archivo se editó en la EC2, se descarta ese archivo y se vuelve a jalar. El código que vale es el de `origin/main`.

```bash
git restore frontend/src/api.ts
git pull origin main
```

## 3. De t3.micro a t3.small, 26 de octubre

La instancia se cambió de tipo en la consola: detener, **Acciones → Configuración de la instancia → Cambiar tipo de instancia**, elegir `t3.small`, volver a iniciar. El disco y el grupo de seguridad se quedaron. La IP privada siguió en `172.31.24.67`.

Todavía no había IP elástica, así que la pública automática pasó de `18.118.112.206` a `3.17.151.210`. Hubo que sustituir la IP vieja en el `.env` del servidor (`DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_ORIGINS`, `TRAZA_PUBLIC_ORIGIN`) y reiniciar con `docker compose -f compose.servidor.yaml up -d`. En una réplica que ya asocia la elástica en la entrada 5, este cambio de IP no se repite.

## 4. Disco de 8 GB a 30 GB, 26 de octubre

En la consola, el volumen `vol-099f58ea131922851` (`/dev/xvda`) se modificó a 30 GB. `df -h` siguió mostrando 8 GB al 96 % porque la partición y el sistema de archivos no crecen solos. En la instancia:

```bash
df -hT /
lsblk
sudo growpart /dev/nvme0n1 1
sudo xfs_growfs -d /
df -h /
```

`lsblk` tiene que mostrar el disco `nvme0n1` en unos 30 GB. `df -hT` en Amazon Linux 2023 dice `xfs`. Si dijera `ext4`, el segundo comando sería `sudo resize2fs /dev/nvme0n1p1`. No hace falta reiniciar. Si `growpart` no existe: `sudo dnf install -y cloud-utils-growpart`.

## 5. IP elástica y GoDaddy, 26 de octubre

Se asignaron dos elásticas. Solo una debía quedar. `77.112.213.200` se asoció a `cfdesign` (`i-07c39f84b1c7b3787`) en la IP privada `172.31.24.67`. AWS soltó `3.17.151.210`. La otra, `18.216.241.38`, se liberó: una elástica sin instancia sigue consumiendo créditos.

En la consola, región Ohio: **Red y seguridad → Direcciones IP elásticas → Asignar** (grupo IPv4 de Amazon) y luego **Acciones → Asociar dirección IP elástica** a la instancia. La SSH se corta; se vuelve a entrar con la elástica.

El DNS de `aulivana.com` está en GoDaddy (`ns55.domaincontrol.com` y `ns56.domaincontrol.com`), no en Route 53. En **Mis productos → aulivana.com → DNS → Agregar**:

| Campo | Valor |
| --- | --- |
| Tipo | A |
| Nombre | `fcdesign` |
| Valor | `77.112.213.200` |
| TTL | 1 hora |

El nombre es solo `fcdesign`. El dominio completo lo duplicaría. El registro se guarda cuando la elástica ya está asociada.

```bash
dig +short A fcdesign.aulivana.com
```

Tiene que imprimir la misma IP de la consola.

## 6. C1: HTTPS y producción, 26 de octubre

El hallazgo C1 era: el servidor público arrancaba en modo desarrollo y sin TLS. El commit `se actualizan archivos para pasarlo a produccion y agregar certidficado ssl` deja el arreglo en `main`.

| Qué | Dónde quedó |
| --- | --- |
| TLS delante de Nginx, redirección del puerto 80 y certificado de `fcdesign.aulivana.com` | `deploy/nginx/servidor.conf` |
| Puertos `80:80` y `443:443`. Ya no se publica 18080. Monta `/etc/letsencrypt` y `/var/www/certbot` | `compose.servidor.yaml` |
| `DJANGO_SETTINGS_MODULE=config.settings.production` | `compose.servidor.yaml` |
| `DEBUG` en falso, cookies `Secure`, clave distinta de las de desarrollo, orígenes `https://`, proxy de confianza y HSTS | `server/config/settings/production.py` |

`SECURE_PROXY_SSL_HEADER` confía en `X-Forwarded-Proto: https`, que Nginx envía con `$scheme`. `DJANGO_SECRET_KEY` no puede ser vacía, `dev-only-change-me` ni `dev-container-not-production`. `DJANGO_CSRF_ORIGINS` tiene que ser `https://fcdesign.aulivana.com`. HSTS sigue en `3600` segundos (una hora). Se alarga a `31536000` en esa misma línea cuando el inicio de sesión por HTTPS ya se haya comprobado.

En el grupo `launch-wizard-1` se dejan 22, 80 y 443. Se borran las reglas de 18080 y 8025 hacia internet. El 80 se conserva porque Nginx redirige a HTTPS y Let's Encrypt renueva por ahí. Postgres y Redis no publican puerto.

El certificado se pide en la instancia con el puerto 80 libre, antes de levantar Nginx:

```bash
sudo dnf install -y certbot
sudo mkdir -p /var/www/certbot
sudo certbot certonly --standalone -d fcdesign.aulivana.com --agree-tos -m correo-del-responsable --non-interactive
```

Tienen que existir `fullchain.pem` y `privkey.pem` en `/etc/letsencrypt/live/fcdesign.aulivana.com/`. El `.env` queda así:

```bash
DJANGO_SECRET_KEY=una-clave-larga-distinta-de-las-de-desarrollo
EMAIL_HOST_PASSWORD=clave-de-aplicacion-de-gmail
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,web,nginx,fcdesign.aulivana.com
DJANGO_CSRF_ORIGINS=https://fcdesign.aulivana.com
TRAZA_PUBLIC_ORIGIN=https://fcdesign.aulivana.com
```

Luego el mismo ciclo de la entrada 2: `build web`, `build runner`, `build nginx` y `up -d --remove-orphans`. La comprobación:

```bash
curl -sI https://fcdesign.aulivana.com/api/v1/auth/csrf/
```

Tiene que verse `strict-transport-security` y `set-cookie` con `Secure`, y el cuerpo `{"ok":true}`. `http://fcdesign.aulivana.com` redirige a `https://`.

La aplicación de escritorio usa el mismo origen, `https://fcdesign.aulivana.com`, en `desktop/src-tauri/src/lib.rs` o en `TRAZA_API_ORIGIN`. Un instalador que siga en `http://…:18080` no guarda la cookie segura. Hay que volver a compilarlo.

Para renovar sin soltar el puerto 80, en `/etc/letsencrypt/renewal/fcdesign.aulivana.com.conf` el authenticator queda en `webroot` y `webroot_path` en `/var/www/certbot`. Después, `sudo certbot renew --dry-run` y `docker compose -f compose.servidor.yaml exec nginx nginx -s reload`.

## Qué no se repite

- No se abre el 18080 ni el 8025.
- No se deja una segunda IP elástica sin asociar.
- No se arranca el servidor público con `config.settings.development`.
- No se editan archivos a mano en la EC2. El cambio entra por `git pull origin main`.
- No se usa `docker compose down -v` si se quieren conservar las cuentas.
