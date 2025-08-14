from typing import Optional

def format_lead_for_confirmation(
    first_name: str,
    last_name: str,
    zip_code: str,
    email: str,
    contact_preference: str,
    vehicle_model: str,
    vehicle_year: Optional[int] = None,
    phone_number: Optional[str] = None,
    notes: Optional[str] = None,
) -> str:
    """
    Formats the collected lead information into a user-friendly confirmation message.

    This tool does not perform any AI analysis; it only formats the data provided by the agent.

    Args:
        first_name: The user's first name.
        last_name: The user's last name.
        zip_code: The user's 5-digit zip code.
        email: The user's email address.
        contact_preference: The user's preferred contact method (e.g., "Email").
        vehicle_model: The vehicle model the user is interested in.
        vehicle_year: The model year of the vehicle.
        phone_number: The user's phone number.
        notes: Any additional notes or questions from the user.

    Returns:
        A formatted string confirming the user's details.
    """
    confirmation_message = "Great, thank you! Please take a moment to review the information below. If everything is correct, I can forward this to a dealership to get you a precise quote.\n\n"
    confirmation_message += f"**First Name:** {first_name}\n"
    confirmation_message += f"**Last Name:** {last_name}\n"
    
    year_str = f"{vehicle_year} " if vehicle_year else ""
    confirmation_message += f"**Vehicle:** {year_str}{vehicle_model}\n"
    
    confirmation_message += f"**Email:** {email}\n"
    if phone_number:
        confirmation_message += f"**Phone:** {phone_number}\n"
    confirmation_message += f"**Contact Preference:** {contact_preference}\n"
    confirmation_message += f"**Zip Code:** {zip_code}\n"
    if notes:
        confirmation_message += f"**Notes:** {notes}\n"
        
    return confirmation_message
