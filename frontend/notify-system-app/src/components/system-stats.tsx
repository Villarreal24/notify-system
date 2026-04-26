import { Box, Grid, Text } from "@chakra-ui/react";

import type { Category, NotificationLog } from "@/lib/api";
import { isOptimisticLogId } from "@/lib/notification-types";

export function SystemStats({
  categories,
  logs,
}: {
  categories: Category[];
  logs: NotificationLog[];
}) {
  const withoutOptimistic = logs.filter((log) => !isOptimisticLogId(log.id));
  const uniqueUsers = new Set(
    withoutOptimistic.map((log) => log.user_id).filter(Boolean),
  ).size;
  const stats = [
    { label: "Categories", value: categories.length },
    { label: "Delivery rows", value: withoutOptimistic.length },
    { label: "Users", value: uniqueUsers },
  ];

  return (
    <Grid templateColumns={{ base: "1fr", sm: "repeat(3, 1fr)" }} gap={3.5}>
      {stats.map((stat) => (
        <Box
          key={stat.label}
          minH="112px"
          rounded="26px"
          borderWidth="1px"
          borderColor="whiteAlpha.200"
          bg="blackAlpha.500"
          p={5}
        >
          <Text
            color="gray.500"
            fontSize="xs"
            fontWeight="extrabold"
            letterSpacing="0.26em"
            textTransform="uppercase"
          >
            {stat.label}
          </Text>
          <Text
            mt={3.5}
            color="white"
            fontSize="4xl"
            fontWeight="black"
            lineHeight="1"
          >
            {stat.value}
          </Text>
        </Box>
      ))}
    </Grid>
  );
}
