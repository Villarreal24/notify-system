"use client";

import {
  Box,
  Button,
  Field,
  Heading,
  NativeSelect,
  Stack,
  Text,
  Textarea,
  chakra,
} from "@chakra-ui/react";
import { useFormStatus } from "react-dom";

import { useNotificationSubmit } from "@/hooks/use-notification-submit";
import type { OptimisticLogAction } from "@/components/notification-dashboard";
import type { Category } from "@/lib/api";

function SubmitButton() {
  const { pending } = useFormStatus();

  return (
    <Button
      type="submit"
      loading={pending}
      loadingText="Encolando"
      colorPalette="teal"
      size="lg"
      rounded="full"
      fontWeight="black"
      color="teal.950"
      bg="linear-gradient(135deg, #5eead4, #14b8a6)"
      boxShadow="0 18px 40px rgba(20, 184, 166, 0.22)"
      _hover={{ filter: "brightness(1.05)", transform: "translateY(-1px)" }}
    >
      Enviar notificacion
    </Button>
  );
}

export function NotificationForm({
  categories,
  onOptimisticLogAction,
}: {
  categories: Category[];
  onOptimisticLogAction: (action: OptimisticLogAction) => void;
}) {
  const [state, formAction] = useNotificationSubmit({
    categories,
    onOptimisticLogAction,
  });

  return (
    <chakra.form
      action={formAction}
      rounded="32px"
      borderWidth="1px"
      borderColor="whiteAlpha.200"
      bg="linear-gradient(145deg, rgba(15, 23, 42, 0.78), rgba(2, 6, 23, 0.68))"
      boxShadow="0 28px 80px rgba(0, 0, 0, 0.35)"
      backdropFilter="blur(22px)"
      p={7}
    >
      <Stack gap={5}>
        <Box>
          <Text
            color="cyan.200"
            fontSize="xs"
            fontWeight="extrabold"
            letterSpacing="0.36em"
            textTransform="uppercase"
          >
            Composer
          </Text>
          <Heading as="h2" mt={2} fontSize="2xl">
            New notification
          </Heading>
        </Box>

        <Field.Root required>
          <Field.Label color="gray.100">Categoria</Field.Label>
          <NativeSelect.Root>
            <NativeSelect.Field
              name="category_id"
              defaultValue=""
              bg="white"
              color="gray.950"
              rounded="xl"
              minH="30px"
            >
              <option value="" disabled>
                Selecciona una categoria
              </option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </NativeSelect.Field>
            <NativeSelect.Indicator color="gray.950" />
          </NativeSelect.Root>
        </Field.Root>

        <Field.Root required>
          <Field.Label color="gray.100">Mensaje</Field.Label>
          <Textarea
            name="message"
            required
            minH="70px"
            bg="white"
            color="gray.950"
            rounded="xl"
            placeholder="Ej. Markets close higher after a volatile session..."
          />
        </Field.Root>

        <SubmitButton />

        {state.message ? (
          <Text
            color={state.status === "success" ? "teal.200" : "red.200"}
            fontSize="sm"
            lineHeight="1.6"
          >
            {state.message}
          </Text>
        ) : null}
      </Stack>
    </chakra.form>
  );
}
