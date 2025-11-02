"""
Serviço centralizado para envio de emails
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from typing import Dict, Any, List, Optional
from wallclub_core.utilitarios.log_control import registrar_log


class EmailService:
    """Serviço centralizado para envio de emails via AWS SES ou outro backend"""

    @staticmethod
    def enviar_email(
        destinatarios: List[str],
        assunto: str,
        template_html: str = None,
        template_context: Dict[str, Any] = None,
        mensagem_texto: str = None,
        remetente: str = None,
        fail_silently: bool = False,
        anexos: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Envia email usando template HTML ou texto simples

        Args:
            destinatarios: Lista de emails destino
            assunto: Assunto do email
            template_html: Caminho do template HTML (ex: 'checkout/emails/link_pagamento.html')
            template_context: Contexto para renderizar template
            mensagem_texto: Mensagem em texto puro (alternativa ao template)
            remetente: Email remetente (usa DEFAULT_FROM_EMAIL se None)
            fail_silently: Se True, não lança exceção em caso de erro
            anexos: Lista de anexos [{'nome': 'file.csv', 'conteudo': bytes, 'tipo': 'text/csv'}]

        Returns:
            Dict com sucesso e mensagem
        """
        try:
            # Remetente padrão
            if not remetente:
                remetente = settings.DEFAULT_FROM_EMAIL

            # Preparar mensagens
            if template_html and template_context:
                html_message = render_to_string(template_html, template_context)
                plain_message = strip_tags(html_message)
            elif mensagem_texto:
                plain_message = mensagem_texto
                html_message = None
            else:
                raise ValueError("Deve fornecer template_html+context ou mensagem_texto")

            # Log antes de enviar
            registrar_log(
                'comum.integracoes',
                f"Tentando enviar email via {settings.EMAIL_BACKEND} - Host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}",
                nivel='DEBUG'
            )
            registrar_log(
                'comum.integracoes',
                f"De: {remetente} -> Para: {', '.join(destinatarios)} - Assunto: {assunto}",
                nivel='DEBUG'
            )

            # Enviar email (com ou sem anexos)
            if anexos:
                # Usar EmailMessage para anexos
                from django.core.mail import EmailMessage

                email_msg = EmailMessage(
                    subject=assunto,
                    body=plain_message,
                    from_email=remetente,
                    to=destinatarios
                )

                # Adicionar versão HTML se existir
                if html_message:
                    email_msg.content_subtype = "html"
                    email_msg.body = html_message

                # Adicionar anexos
                for anexo in anexos:
                    email_msg.attach(
                        filename=anexo['nome'],
                        content=anexo['conteudo'],
                        mimetype=anexo.get('tipo', 'application/octet-stream')
                    )

                num_enviados = email_msg.send(fail_silently=fail_silently)
            else:
                # Usar send_mail para emails simples
                num_enviados = send_mail(
                    subject=assunto,
                    message=plain_message,
                    from_email=remetente,
                    recipient_list=destinatarios,
                    html_message=html_message,
                    fail_silently=fail_silently,
                )

            registrar_log(
                'comum.integracoes',
                f"send_mail() retornou: {num_enviados}",
                nivel='DEBUG'
            )

            if num_enviados > 0:
                registrar_log(
                    'comum.integracoes',
                    f"✅ Email enviado com sucesso: {assunto} -> {', '.join(destinatarios)}"
                )
                return {
                    'sucesso': True,
                    'mensagem': f'Email enviado para {len(destinatarios)} destinatário(s)'
                }
            else:
                registrar_log(
                    'comum.integracoes',
                    f"Email não enviado (retorno 0): {assunto}",
                    nivel='WARNING'
                )
                return {
                    'sucesso': False,
                    'mensagem': 'Email não foi enviado (retorno 0)'
                }

        except Exception as e:
            registrar_log(
                'comum.integracoes',
                f"Erro ao enviar email: {str(e)}",
                nivel='ERROR'
            )

            if not fail_silently:
                raise

            return {
                'sucesso': False,
                'mensagem': f'Erro ao enviar email: {str(e)}'
            }

    @staticmethod
    def enviar_email_simples(
        destinatario: str,
        assunto: str,
        mensagem: str,
        fail_silently: bool = False
    ) -> Dict[str, Any]:
        """
        Atalho para enviar email simples de texto para um único destinatário

        Args:
            destinatario: Email do destinatário
            assunto: Assunto do email
            mensagem: Mensagem em texto puro
            fail_silently: Se True, não lança exceção em caso de erro

        Returns:
            Dict com sucesso e mensagem
        """
        return EmailService.enviar_email(
            destinatarios=[destinatario],
            assunto=assunto,
            mensagem_texto=mensagem,
            fail_silently=fail_silently
        )
