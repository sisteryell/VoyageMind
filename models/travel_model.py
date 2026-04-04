"""Business-logic layer that orchestrates the multi-agent travel planning pipeline.

Flow for ``run_plan``:
    1. Run selected travel-style agents in parallel.
    2. Feed their results into the AggregatorAgent for ranking.
    3. Pad recommendations to *city_count* from agent results if needed.
    4. Run ItineraryAgent in parallel for each recommended city.

``run_chat`` delegates directly to the ChatAgent for free-form Q&A.
"""

import asyncio
from agents import AggregatorAgent, ChatAgent, ItineraryAgent, TRAVEL_STYLE_AGENT_MAP
from schemas import PlanResponse


class TravelModel:
    """Coordinates specialist agents into a complete travel plan or chat answer."""

    @staticmethod
    def _ensure_city_count(
        recommendations: list[dict],
        agent_results: list[dict],
        city_count: int,
    ) -> list[dict]:
        """Guarantee exactly *city_count* recommendations by back-filling
        from specialist agent results when the aggregator returns fewer."""
        def normalize_city(city: str) -> str:
            return city.strip().lower()
        def extract_city(rec: dict) -> str:
            return str(rec.get("city", "")).strip()
        def extract_reason(rec: dict) -> str:
            return str(rec.get("reason", "Selected from specialist agent insights.")).strip()

        final_recommendations = []
        seen_cities = set()

        for rec in recommendations:
            city = extract_city(rec)
            if not city:
                continue
            key = normalize_city(city)
            if key in seen_cities:
                continue
            final_recommendations.append({
                "city": city,
                "reason": extract_reason(rec),
            })
            seen_cities.add(key)

            if len(final_recommendations) == city_count:
                return final_recommendations
        
        for agent in agent_results:
            for rec in agent.get("recommendations", []):
                city = extract_city(rec)
                if not city:
                    continue
                key = normalize_city(city)
                if key in seen_cities:
                    continue
                final_recommendations.append({
                    "city": city,
                    "reason": extract_reason(rec),
                })
                seen_cities.add(key)

                if len(final_recommendations) == city_count:
                    return final_recommendations
        
        return final_recommendations

    async def run_plan(
        self,
        country: str,
        budget: str,
        duration: int,
        city_count: int,
        travel_styles: list[str],
        session_id: str
    ) -> PlanResponse:
        """
        Execute the full plan pipeline: style agents → aggregator → itineraries.
        """

        # select agents based on requested travel styles, or run all if none specified
        selected = {}
        if travel_styles:
            for style in travel_styles:
                if style in TRAVEL_STYLE_AGENT_MAP:
                    selected[style] = TRAVEL_STYLE_AGENT_MAP[style]
        else:
            selected = TRAVEL_STYLE_AGENT_MAP

        # Run selected style agents in parallel and gather their recommendations
        tasks = []
        for cls in selected.values():
            tasks.append(cls().run(
                country=country,
                budget=budget,
                duration=duration,
                city_count=city_count,
                travel_styles=travel_styles))
        style_results = await asyncio.gather(*(tasks))


        # Build agent results for the aggregator, pairing each style with its recommendations
        agent_results = []
        styles = list(selected.keys())

        for i in range(len(styles)):
            style = styles[i]
            result = style_results[i]

            agent_results.append({
                "agent_name": style,
                "recommendations": result["recommendations"],
            })

        # Run the aggregator to get a final ranked list of recommendations
        final_result = await AggregatorAgent().run(
            country=country,
            budget=budget,
            duration=duration,
            city_count=city_count,
            travel_styles=travel_styles,
            agent_results=agent_results,
        )

        final_recommendations = self._ensure_city_count(
            recommendations=final_result["recommendations"],
            agent_results=agent_results,
            city_count=city_count,
        )


        # Run itinerary agent
        itinerary_tasks = []
        for rec in final_recommendations:
            tasks = ItineraryAgent().run(
                country=country,
                budget=budget,
                duration=duration,
                city_count=city_count,
                travel_styles=travel_styles,
                city=rec["city"],
                reason=rec["reason"]
            )
            itinerary_tasks.append(tasks)
        itinerary_results = await asyncio.gather(*(itinerary_tasks))


        # Build itineraries with city and day-by-day plan for each recommended city
        itineraries = []
        for i in range(len(final_recommendations)):
            rec = final_recommendations[i]
            itinerary = itinerary_results[i]
            itineraries.append({
                "city": rec["city"],
                "days": itinerary["days"],
            })

        agent_details = {}
        for style, result in zip(styles, style_results):
            agent_details[style] = result["recommendations"]

        result = {
            "country": country,
            "budget": budget,
            "duration": duration,
            "city_count": city_count,
            "travel_styles": travel_styles,
            "recommendations": final_recommendations,
            "itineraries": itineraries,
            "agent_details": agent_details,
        }

        return PlanResponse(**result, session_id=session_id)

    async def run_chat(
        self,
        country: str,
        budget: str,
        duration: int,
        travel_styles: list[str],
        recommendations: list[dict],
        question: str
    ) -> dict:
        """Send a follow-up question to the ChatAgent with trip context."""
        return await ChatAgent().run(
            country=country,
            budget=budget,
            duration=duration,
            travel_styles=travel_styles,
            recommendations=recommendations,
            question=question
        )
